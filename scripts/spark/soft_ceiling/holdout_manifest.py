#!/usr/bin/env python3
"""Freeze the test-split surface for a one-time held-out eval. No torch, no scoring.

Publish-readiness steps 2c / 3a / 3b. Writes a manifest that must be committed
before any model is scored on ``split=test``:

- row-ID hashes for each slice (unbind all / clean / oov-filler; classify clean)
- exclusions: rows in any listed model's force/hard files, or text in train
- per-lineage classify counts
- sha256 of each pinned ``model.safetensors``
- the metric list, fixed in advance

  python scripts/spark/soft_ceiling/holdout_manifest.py \
      --model DIR --model DIR2 --trained F.jsonl [--trained ...] --out MANIFEST.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "shadow"))

from hyperlexical.export import export_dataset  # noqa: E402
from hyperlexical.provenance import provenance  # noqa: E402
from hyperlexical.soft_ceiling import clean_surface, load_jsonl_keys, oov_filler_surface, row_key  # noqa: E402

METRICS = {
    "unbind": ["unbind_exact", "unbind_token_f1", "unbind_slot_f1"],
    "unbind_slices": ["all", "clean", "oov_filler", "by_role_scheme"],
    "classify": ["accuracy", "macro_f1", "ece_15_bins", "abstain_rate"],
    "report_by_label_class": ["OBSERVED", "INFERRED"],
    "baselines": ["stub", "spec004_probe"],
}


def ids_sha256(rows: list[dict]) -> str:
    keys = sorted({"|".join((str(r.get("task")), *row_key(r))) for r in rows})
    return hashlib.sha256("\n".join(keys).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build(rows: list[dict], trained: set) -> dict:
    train_unbind = [r for r in rows if r.get("task") == "unbind" and r.get("split") == "train"]
    train_all = [r for r in rows if r.get("split") == "train"]
    test_unbind = [r for r in rows if r.get("task") == "unbind" and r.get("split") == "test"]
    test_classify = [r for r in rows if r.get("task") == "classify" and r.get("split") == "test"]
    u_clean, u_acct = clean_surface(test_unbind, train_rows=train_all, trained_keys=trained)
    u_oov = oov_filler_surface(u_clean, train_unbind)
    c_clean, c_acct = clean_surface(test_classify, train_rows=train_all, trained_keys=trained)
    slices = {
        "unbind_all": test_unbind,
        "unbind_clean": u_clean,
        "unbind_oov_filler": u_oov,
        "classify_clean": c_clean,
    }
    return {
        "slices": {
            name: {
                "n": len(s),
                "ids_sha256": ids_sha256(s),
                "by_role_scheme": dict(Counter(str(r.get("role_scheme")) for r in s)) if name.startswith("unbind") else None,
                "by_class": dict(Counter(str(r.get("class")) for r in s)),
            }
            for name, s in slices.items()
        },
        "exclusions": {"unbind": u_acct, "classify": c_acct},
        "classify_by_lineage": dict(Counter(str(r.get("lineage")) for r in c_clean)),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", action="append", required=True, help="pinned train-out dir (repeat)")
    p.add_argument("--trained", action="append", default=[], help="force/hard jsonl any listed model trained on")
    p.add_argument("--env", default="", help="recipe env json (export must match training)")
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)
    if args.env:
        os.environ.update(json.loads(Path(args.env).read_text()))
    trained = set()
    for path in args.trained:
        trained |= load_jsonl_keys(path)
    bundle = export_dataset(REPO, include_live=True)
    body = build(bundle["rows"], trained)
    models = {}
    for m in args.model:
        d = Path(m)
        w = d / "model.safetensors" if (d / "model.safetensors").is_file() else d / "best" / "model.safetensors"
        models[Path(os.path.realpath(d)).name] = {"path": str(d), "safetensors_sha256": file_sha256(w)}
    out = {
        "schema": "hyperlex.holdout_manifest.v0.1",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "status": "FROZEN_NOT_SCORED",
        "split": "test",
        "models": models,
        "trained_files": args.trained,
        "n_trained_keys": len(trained),
        "metrics": METRICS,
        "rules": [
            "Score each listed model once on these exact row-ID hashes.",
            "No selection, tuning, or calibration on test after scoring; test is burned for selection.",
            "Calibration (temperature, abstain threshold) is fitted on clean val before scoring and frozen here.",
            "Any future climb draws and hashes a new holdout before training.",
        ],
        "brier": None,
        **body,
        **provenance(REPO),
    }
    Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: out[k] for k in ("status", "models", "exclusions")} | {"slices": {k: v["n"] for k, v in out["slices"].items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
