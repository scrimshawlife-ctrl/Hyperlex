#!/usr/bin/env python3
"""Score a checkpoint on broad OBSERVED unbind val: all / clean / oov slices.

Canonical replacement for ``~/hlx/eval_broad_observed.py`` (archived next to
this file). "clean" drops rows in the candidate's force-train / hard-atom files
and any text in train; "oov" further keeps rows whose fillers are unseen in
train. The gate must read ``overlap`` for the slice it compares.

Run on Spark inside the training container (torch + local trunk):

  python scripts/spark/soft_ceiling/eval_broad.py --model DIR \
      --force FORCE.jsonl [--hard HARD.jsonl] --out OUT.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "shadow"))

from hyperlexical.export import export_dataset  # noqa: E402
from hyperlexical.provenance import provenance  # noqa: E402
from hyperlexical.release_set import maybe_release  # noqa: E402
from hyperlexical.soft_ceiling import clean_surface, load_jsonl_keys, oov_filler_surface, overlap  # noqa: E402


def _model_root(model: Path) -> Path:
    if (model / "model.safetensors").is_file():
        return model
    if (model / "best" / "model.safetensors").is_file():
        return model / "best"
    return model


def surfaces(rows: list[dict], trained_keys: set) -> dict:
    unbind = [r for r in rows if r.get("task") == "unbind"]
    train = [r for r in unbind if r.get("split") == "train"]
    val_obs = [
        r for r in unbind if r.get("split") == "val" and str(r.get("class") or "").upper() == "OBSERVED"
    ]
    clean, acct = clean_surface(val_obs, train_rows=train, trained_keys=trained_keys)
    oov = oov_filler_surface(clean, train)
    return {"all": val_obs, "clean": clean, "oov": oov, "accounting": acct}


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--force", action="append", default=[], help="force-train jsonl the candidate trained on")
    p.add_argument("--hard", action="append", default=[], help="hard-atom jsonl the candidate trained on")
    p.add_argument("--trunk", default=os.environ.get("HYPERLEX_TRUNK_DIR", str(Path.home() / ".hyperlex/models/trunks/ModernBERT-base")))
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)

    os.environ.pop("HYPERLEX_UNBIND_FORCE_TRAIN_PATH", None)
    trained = set()
    for path in args.force + args.hard:
        trained |= load_jsonl_keys(path)
    bundle = export_dataset(REPO, include_live=True)
    rows, release_stats = maybe_release(bundle["rows"])
    surf = surfaces(rows, trained)

    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer
    from hyperlexical.eval_forward import (
        _load_filler_head,
        _load_maps,
        _weight_parts,
        apply_encoder_trainable,
        score_unbind_exact,
    )
    from hyperlexical.layout import HIDDEN

    model = Path(args.model)
    root = _model_root(model)
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tok = AutoTokenizer.from_pretrained(args.trunk, local_files_only=True)
    enc = AutoModel.from_pretrained(args.trunk, local_files_only=True)
    fs, et, hb = _weight_parts(root / "model.safetensors", torch)
    apply_encoder_trainable(enc, et)
    maps = _load_maps(model if (model / "layout.json").is_file() else root, hb)
    fh = _load_filler_head(nn, int(getattr(enc.config, "hidden_size", HIDDEN)), fs, maps)
    enc.to(dev)
    fh.to(dev)

    slices = {}
    for name in ("all", "clean", "oov"):
        rows = surf[name]
        scored = score_unbind_exact(enc, fh, tok, maps, rows, dev) if rows else {"unbind_exact": None, "n_unbind_eval": 0}
        slices[name] = {
            "unbind_exact": scored.get("unbind_exact"),
            "n_scored": int(scored.get("n_unbind_eval") or 0),
            "overlap": overlap(rows, trained),
            "unbind_token_f1": scored.get("unbind_token_f1"),
            "unbind_exact_strict": scored.get("unbind_exact_strict"),
            "unbind_token_f1_strict": scored.get("unbind_token_f1_strict"),
            "unbind_slot_f1_strict": scored.get("unbind_slot_f1_strict"),
        }
    out = {
        "schema": "hyperlex.broad_observed_eval.v0.2",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "model": str(model),
        "trained_files": args.force + args.hard,
        "n_trained_keys": len(trained),
        "accounting": surf["accounting"],
        "release_set": release_stats,
        "slices": slices,
        "brier": None,
        **provenance(REPO),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("model", "accounting", "slices")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
