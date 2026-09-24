#!/usr/bin/env python3
"""Fit lineage calibration on clean classify val. Never reads split=test.

Publish-readiness step 5a. Temperature scaling (grid search on NLL) plus an
abstain threshold: the smallest max-prob cutoff whose selective accuracy on
clean val reaches ``--target-accuracy``. Output is frozen into the holdout
manifest before test is scored.

  python scripts/spark/soft_ceiling/calibrate_classify.py --model DIR \
      --trained F.jsonl [--trained ...] --env ENV.json --out CAL.json
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

from hyperlexical.export import export_dataset  # noqa: E402
from hyperlexical.layout import FAMILIES, HIDDEN, MAX_LEN  # noqa: E402
from hyperlexical.provenance import provenance  # noqa: E402
from hyperlexical.release_set import maybe_release  # noqa: E402
from hyperlexical.soft_ceiling import clean_surface, load_jsonl_keys  # noqa: E402

TEMPS = [round(0.5 + 0.05 * i, 2) for i in range(191)]  # 0.5 .. 10.0


def softmax(logits: list[float], t: float) -> list[float]:
    m = max(x / t for x in logits)
    e = [math.exp(x / t - m) for x in logits]
    s = sum(e)
    return [v / s for v in e]


def nll(logit_rows: list[list[float]], gold: list[int], t: float) -> float:
    return -sum(math.log(max(softmax(l, t)[g], 1e-12)) for l, g in zip(logit_rows, gold)) / max(1, len(gold))


def ece(probs: list[list[float]], gold: list[int], bins: int = 15) -> float:
    tot, err = len(gold), 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i, p in enumerate(probs) if lo < max(p) <= hi or (b == 0 and max(p) == 0)]
        if not idx:
            continue
        conf = sum(max(probs[i]) for i in idx) / len(idx)
        acc = sum(1 for i in idx if probs[i].index(max(probs[i])) == gold[i]) / len(idx)
        err += len(idx) / tot * abs(conf - acc)
    return err


def fit(logit_rows: list[list[float]], gold: list[int], target_accuracy: float) -> dict:
    t_best = min(TEMPS, key=lambda t: nll(logit_rows, gold, t))
    raw = [softmax(l, 1.0) for l in logit_rows]
    cal = [softmax(l, t_best) for l in logit_rows]
    acc = sum(1 for p, g in zip(cal, gold) if p.index(max(p)) == g) / max(1, len(gold))
    threshold, coverage, sel_acc = None, 0.0, None
    for cut in sorted({round(max(p), 4) for p in cal}):
        keep = [i for i, p in enumerate(cal) if max(p) >= cut]
        if not keep:
            break
        a = sum(1 for i in keep if cal[i].index(max(cal[i])) == gold[i]) / len(keep)
        if a >= target_accuracy:
            threshold, coverage, sel_acc = cut, len(keep) / len(cal), a
            break
    return {
        "temperature": t_best,
        "nll_raw": nll(logit_rows, gold, 1.0),
        "nll_calibrated": nll(logit_rows, gold, t_best),
        "ece_raw": ece(raw, gold),
        "ece_calibrated": ece(cal, gold),
        "accuracy": acc,
        "abstain_threshold": threshold,
        "coverage_at_threshold": coverage,
        "selective_accuracy": sel_acc,
        "target_accuracy": target_accuracy,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--trained", action="append", default=[])
    p.add_argument("--env", default="")
    p.add_argument("--target-accuracy", type=float, default=0.9)
    p.add_argument("--trunk", default=os.environ.get("HYPERLEX_TRUNK_DIR", str(Path.home() / ".hyperlex/models/trunks/ModernBERT-base")))
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)
    if args.env:
        os.environ.update(json.loads(Path(args.env).read_text()))
    trained = set()
    for f in args.trained:
        trained |= load_jsonl_keys(f)
    rows, release_stats = maybe_release(export_dataset(REPO, include_live=True)["rows"])
    train_all = [r for r in rows if r.get("split") == "train"]
    val_cls = [r for r in rows if r.get("task") == "classify" and r.get("split") == "val"]
    val_clean, acct = clean_surface(val_cls, train_rows=train_all, trained_keys=trained)
    assert all(r.get("split") != "test" for r in val_clean)

    import torch
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.save_pretrained import split_weight_tensors

    model = Path(args.model)
    root = model if (model / "model.safetensors").is_file() else model / "best"
    split = split_weight_tensors(load_file(str(root / "model.safetensors"), device="cpu"))
    tok = AutoTokenizer.from_pretrained(args.trunk, local_files_only=True)
    enc = AutoModel.from_pretrained(args.trunk, local_files_only=True)
    apply_encoder_trainable(enc, split["encoder"])
    head = torch.nn.Linear(HIDDEN, len(FAMILIES))
    head.load_state_dict(split["classify"])
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    enc.to(dev).eval()
    head.to(dev).eval()
    fam_of = {f: i for i, f in enumerate(FAMILIES)}
    logits, gold, cls = [], [], []
    with torch.no_grad():
        for r in val_clean:
            if r.get("lineage") not in fam_of:
                continue
            e = tok([r["text"]], truncation=True, max_length=MAX_LEN, return_tensors="pt").to(dev)
            logits.append(head(enc(**e).last_hidden_state[:, 0])[0].tolist())
            gold.append(fam_of[r["lineage"]])
            cls.append(str(r.get("class")))
    out = {
        "schema": "hyperlex.classify_calibration.v0.1",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "model": str(model),
        "fit_split": "val",
        "surface": acct,
        "release_set": release_stats,
        "n": len(gold),
        "by_label_class": dict(Counter(cls)),
        "gold_by_family": dict(Counter(FAMILIES[g] for g in gold)),
        "all": fit(logits, gold, args.target_accuracy),
        "observed_only": fit([l for l, c in zip(logits, cls) if c == "OBSERVED"], [g for g, c in zip(gold, cls) if c == "OBSERVED"], args.target_accuracy)
        if "OBSERVED" in cls
        else None,
        "brier": None,
        **provenance(REPO),
    }
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("n", "by_label_class", "all", "observed_only")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
