#!/usr/bin/env python3
"""Score a Hyperlex encoder on broad OBSERVED unbind val (no force shrink).

Used by soft_ceiling_tiebreak when force-fair == 1.0: promote requires
candidate broad OBSERVED exact > morph65 baseline 0.889763779527559 n=254.

Env:
  HLX_FAIR_MODEL   model dir (default morph65 BEST)
  HLX_BROAD_OUT    output JSON path
  HLX_BROAD_PRIV   optional private copy dir
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/morpheus/Hyperlex")
sys.path.insert(0, str(ROOT / "scripts/shadow"))

import torch
from torch import nn
from transformers import AutoModel, AutoTokenizer
from hyperlexical.export import export_dataset, repo_root
from hyperlexical.layout import HIDDEN
from hyperlexical.eval_forward import (
    apply_encoder_trainable,
    score_unbind_exact,
    _weight_parts,
    _load_maps,
    _load_filler_head,
)

TRUNK = Path(
    os.environ.get(
        "HYPERLEX_TRUNK_DIR",
        str(Path.home() / ".hyperlex/models/trunks/ModernBERT-base"),
    )
)
MODEL = Path(
    os.environ.get(
        "HLX_FAIR_MODEL",
        str(Path.home() / ".hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph65"),
    )
)
OUT = Path(
    os.environ.get(
        "HLX_BROAD_OUT",
        "/home/morpheus/hlx/broad-eval-observed.json",
    )
)
PRIV = Path(os.environ["HLX_BROAD_PRIV"]) if os.environ.get("HLX_BROAD_PRIV") else None

# Authorize-time pin (historical). Live soft_ceiling compare uses PRIOR eval.
PIN_EXACT = 0.889763779527559
PIN_N = 254


def _model_root(model: Path) -> Path:
    if (model / "model.safetensors").is_file():
        return model
    if (model / "best" / "model.safetensors").is_file():
        return model / "best"
    return model


def main() -> int:
    os.environ.pop("HYPERLEX_UNBIND_FORCE_TRAIN_PATH", None)
    bundle = export_dataset(repo_root(), include_live=True)
    rows = [r for r in bundle["rows"] if r.get("task") == "unbind"]
    val = [r for r in rows if r.get("split") == "val"]
    val_obs = [r for r in val if str(r.get("class") or "").upper() == "OBSERVED"]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    root = _model_root(MODEL)
    weight_path = root / "model.safetensors"
    assert weight_path.is_file(), weight_path
    maps_dir = MODEL if (MODEL / "atom_map.json").is_file() else root

    tok = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    enc = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    filler_state, encoder_tensors, heads_blob = _weight_parts(weight_path, torch)
    apply_encoder_trainable(enc, encoder_tensors)
    maps = _load_maps(maps_dir, heads_blob)
    hidden = int(getattr(enc.config, "hidden_size", HIDDEN))
    filler_head = _load_filler_head(nn, hidden, filler_state, maps)
    enc.to(device)
    filler_head.to(device)

    scored = score_unbind_exact(enc, filler_head, tok, maps, val_obs, device)
    exact = float(scored.get("unbind_exact") or 0)
    n = int(scored.get("n_unbind_eval") or scored.get("n") or 0)

    out = {
        "schema": "hyperlex.broad_observed_eval.v0.1",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "gate": "soft_ceiling_tiebreak",
        "model": str(MODEL),
        "force": None,
        "unbind_exact": exact,
        "n_scored": n,
        "scored": scored,
        "authorize_pin": {
            "seed": "seed-morph65",
            "unbind_exact": PIN_EXACT,
            "n": PIN_N,
            "note": "Historical at gate authorize; live SoT may differ",
        },
        "note": (
            "Broad OBSERVED val without apply_unbind_force_train. "
            "soft_ceiling: compare candidate vs PRIOR on this same live surface."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    if PRIV is not None:
        PRIV.mkdir(parents=True, exist_ok=True)
        (PRIV / OUT.name).write_text(OUT.read_text())
    print(
        json.dumps(
            {k: out[k] for k in ["unbind_exact", "n_scored", "model"]},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
