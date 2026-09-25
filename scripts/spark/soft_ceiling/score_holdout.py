#!/usr/bin/env python3
"""Score models once on a frozen holdout manifest (split=test). D7.

Refuses to run unless the recomputed slices match the manifest row-ID hashes
exactly, and refuses to overwrite an existing output. Calibration (temperature,
abstain threshold) comes from val-fitted JSON; nothing is fitted on test.

Baselines: ``unbind_copy_token`` predicts each atom's own token as its filler
(unbind on whitespace atoms is close to a copy task). ``classify_majority_train``
predicts the most common train lineage.

  python scripts/spark/soft_ceiling/score_holdout.py --manifest M.json \
      --model NAME=DIR[=CAL.json] [--model ...] --env ENV.json --out OUT.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "shadow"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from calibrate_classify import ece, softmax  # noqa: E402
from holdout_manifest import build  # noqa: E402
from hyperlexical.export import export_dataset  # noqa: E402
from hyperlexical.layout import FAMILIES, HIDDEN, MAX_LEN  # noqa: E402
from hyperlexical.provenance import provenance  # noqa: E402
from hyperlexical.release_set import maybe_release  # noqa: E402
from hyperlexical.soft_ceiling import clean_surface, load_jsonl_keys, oov_filler_surface  # noqa: E402


def macro_f1(pred: list[int], gold: list[int]) -> float:
    classes = sorted(set(gold) | set(pred))
    f1s = []
    for c in classes:
        tp = sum(1 for p, g in zip(pred, gold) if p == c and g == c)
        fp = sum(1 for p, g in zip(pred, gold) if p == c and g != c)
        fn = sum(1 for p, g in zip(pred, gold) if p != c and g == c)
        f1s.append(0.0 if tp == 0 else 2 * tp / (2 * tp + fp + fn))
    return sum(f1s) / max(1, len(f1s))


def copy_baseline(rows: list[dict]) -> float | None:
    pairs = [(r, r.get("fillers") or []) for r in rows if r.get("fillers")]
    if not pairs:
        return None
    hit = 0
    for r, fillers in pairs:
        toks = [t.split(":", 1)[-1].lower() for t in str(r.get("text") or "").split()]
        hit += int(all(str(f).lower() in toks for f in fillers))
    return hit / len(pairs)


def slices_from(rows: list[dict], trained: set) -> dict:
    train_unbind = [r for r in rows if r.get("task") == "unbind" and r.get("split") == "train"]
    train_all = [r for r in rows if r.get("split") == "train"]
    test_unbind = [r for r in rows if r.get("task") == "unbind" and r.get("split") == "test"]
    test_cls = [r for r in rows if r.get("task") == "classify" and r.get("split") == "test"]
    u_clean, _ = clean_surface(test_unbind, train_rows=train_all, trained_keys=trained)
    c_clean, _ = clean_surface(test_cls, train_rows=train_all, trained_keys=trained)
    return {
        "unbind_all": test_unbind,
        "unbind_clean": u_clean,
        "unbind_oov_filler": oov_filler_surface(u_clean, train_unbind),
        "classify_clean": c_clean,
        "_train_all": train_all,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--model", action="append", required=True, help="NAME=DIR[=CALIBRATION.json]")
    p.add_argument("--env", default="")
    p.add_argument("--trunk", default=os.environ.get("HYPERLEX_TRUNK_DIR", str(Path.home() / ".hyperlex/models/trunks/ModernBERT-base")))
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)
    if Path(args.out).exists():
        raise SystemExit(f"REFUSE: {args.out} exists; the holdout is scored once")
    if args.env:
        os.environ.update(json.loads(Path(args.env).read_text()))
    manifest = json.loads(Path(args.manifest).read_text())
    if manifest.get("status") != "FROZEN_NOT_SCORED":
        raise SystemExit("REFUSE: manifest is not FROZEN_NOT_SCORED")
    trained = set()
    for f in manifest["trained_files"]:
        trained |= load_jsonl_keys(f)
    rows, release_stats = maybe_release(export_dataset(REPO, include_live=True)["rows"])
    frozen = build(rows, trained)["slices"]
    for name, meta in manifest["slices"].items():
        if frozen[name]["ids_sha256"] != meta["ids_sha256"] or frozen[name]["n"] != meta["n"]:
            raise SystemExit(f"REFUSE: slice {name} does not match manifest (data or code drifted)")
    sl = slices_from(rows, trained)

    import torch
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer
    from hyperlexical.eval_forward import _load_filler_head, _load_maps, _weight_parts, apply_encoder_trainable, score_unbind_exact
    from hyperlexical.save_pretrained import split_weight_tensors

    fam_of = {f: i for i, f in enumerate(FAMILIES)}
    train_lineage = Counter(r.get("lineage") for r in sl["_train_all"] if r.get("task") == "classify" and r.get("lineage") in fam_of)
    majority = fam_of[train_lineage.most_common(1)[0][0]]
    cls_rows = [r for r in sl["classify_clean"] if r.get("lineage") in fam_of]
    gold = [fam_of[r["lineage"]] for r in cls_rows]
    label_class = [str(r.get("class")) for r in cls_rows]
    baselines = {
        "unbind_copy_token": {k: copy_baseline(sl[k]) for k in ("unbind_all", "unbind_clean", "unbind_oov_filler")},
        "classify_majority_train": {"family": FAMILIES[majority], "accuracy": sum(1 for g in gold if g == majority) / max(1, len(gold))},
    }
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tok = AutoTokenizer.from_pretrained(args.trunk, local_files_only=True)
    results = {}
    for spec in args.model:
        parts = spec.split("=")
        name, mdir = parts[0], Path(parts[1])
        cal = json.loads(Path(parts[2]).read_text())["all"] if len(parts) > 2 else None
        temp = float(cal["temperature"]) if cal else 1.0
        thr = cal.get("abstain_threshold") if cal else None
        root = mdir if (mdir / "model.safetensors").is_file() else mdir / "best"
        enc = AutoModel.from_pretrained(args.trunk, local_files_only=True)
        fs, et, hb = _weight_parts(root / "model.safetensors", torch)
        apply_encoder_trainable(enc, et)
        maps = _load_maps(mdir if (mdir / "config.json").is_file() else root, hb)
        fh = _load_filler_head(torch.nn, HIDDEN, fs, maps)
        split = split_weight_tensors(load_file(str(root / "model.safetensors"), device="cpu"))
        head = torch.nn.Linear(HIDDEN, len(FAMILIES))
        head.load_state_dict(split["classify"])
        enc.to(dev).eval()
        fh.to(dev).eval()
        head.to(dev).eval()
        unbind = {}
        for k in ("unbind_all", "unbind_clean", "unbind_oov_filler"):
            s = score_unbind_exact(enc, fh, tok, maps, sl[k], dev) if sl[k] else {}
            by_scheme = {}
            by_scheme_strict = {}
            for scheme in sorted({str(r.get("role_scheme")) for r in sl[k]}):
                sub = [r for r in sl[k] if str(r.get("role_scheme")) == scheme]
                scheme_scored = score_unbind_exact(enc, fh, tok, maps, sub, dev)
                by_scheme[scheme] = scheme_scored.get("unbind_exact")
                by_scheme_strict[scheme] = scheme_scored.get("unbind_exact_strict")
            unbind[k] = {
                "n": len(sl[k]),
                "unbind_exact": s.get("unbind_exact"),
                "unbind_token_f1": s.get("unbind_token_f1"),
                "unbind_slot_f1": s.get("unbind_slot_f1"),
                "unbind_exact_strict": s.get("unbind_exact_strict"),
                "unbind_token_f1_strict": s.get("unbind_token_f1_strict"),
                "unbind_slot_f1_strict": s.get("unbind_slot_f1_strict"),
                "by_role_scheme": by_scheme,
                "by_role_scheme_strict": by_scheme_strict,
            }
        logits = []
        with torch.no_grad():
            for r in cls_rows:
                e = tok([r["text"]], truncation=True, max_length=MAX_LEN, return_tensors="pt").to(dev)
                logits.append(head(enc(**e).last_hidden_state[:, 0])[0].tolist())
        probs = [softmax(l, temp) for l in logits]
        pred = [pp.index(max(pp)) for pp in probs]

        def cls_metrics(idx):
            g = [gold[i] for i in idx]
            pr = [pred[i] for i in idx]
            pb = [probs[i] for i in idx]
            out = {"n": len(idx), "accuracy": sum(1 for a, b in zip(pr, g) if a == b) / max(1, len(idx)), "macro_f1": macro_f1(pr, g), "ece_15_bins": ece(pb, g) if idx else None}
            if thr is not None and idx:
                keep = [j for j, q in enumerate(pb) if max(q) >= thr]
                out["abstain_rate"] = 1 - len(keep) / len(idx)
                out["selective_accuracy"] = sum(1 for j in keep if pr[j] == g[j]) / max(1, len(keep))
            return out

        allidx = list(range(len(gold)))
        results[name] = {
            "model": str(mdir),
            "calibration": {"temperature": temp, "abstain_threshold": thr},
            "unbind": unbind,
            "classify": {
                "all": cls_metrics(allidx),
                "by_label_class": {c: cls_metrics([i for i in allidx if label_class[i] == c]) for c in sorted(set(label_class))},
            },
        }
        del enc
    out = {
        "schema": "hyperlex.holdout_scores.v0.1",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "manifest": args.manifest,
        "manifest_verified": True,
        "release_set": release_stats,
        "baselines": baselines,
        "results": results,
        "brier": None,
        **provenance(REPO),
    }
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"baselines": baselines, "results": {k: {"unbind": {s: v["unbind_exact"] for s, v in r["unbind"].items()}, "unbind_strict": {s: v.get("unbind_exact_strict") for s, v in r["unbind"].items()}, "classify": r["classify"]["all"]} for k, r in results.items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
