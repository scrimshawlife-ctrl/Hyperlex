#!/usr/bin/env python3
"""Fair-eval morph65 BEST on morph77 force surface after SoT clean + acquire settle."""
from __future__ import annotations
import json, os, sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path("/home/morpheus/Hyperlex")
sys.path.insert(0, str(ROOT / "scripts/shadow"))

import torch
from torch import nn
from transformers import AutoModel, AutoTokenizer
from hyperlexical.export import export_dataset, repo_root
from hyperlexical.layout import HIDDEN
from hyperlexical.eval_forward import (
    apply_encoder_trainable, score_unbind_exact, _weight_parts, _load_maps, _load_filler_head,
)
from hyperlexical.unbind_recipe import apply_unbind_force_train

TRUNK = Path(os.environ.get("HYPERLEX_TRUNK_DIR", str(Path.home() / ".hyperlex/models/trunks/ModernBERT-base")))
MODEL = Path(os.environ.get("HLX_FAIR_MODEL", str(Path.home() / ".hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph65")))
FORCE = Path("/home/morpheus/hlx/force_train_morph78_expanded.jsonl")
HARD = Path("/home/morpheus/hlx/hard_atoms_train_morph78.jsonl")
OUT = Path("/home/morpheus/hlx/fair-eval-morph65-morph78.json")
PROMOTE = Path("/home/morpheus/hlx-private/p1-spark-morph78-val-settle-20260923/PROMOTE_SUMMARY.json")
PRIV = Path("/home/morpheus/hlx-private/p1-spark-morph78-val-settle-20260923")
TRAIN_PRIV = Path("/home/morpheus/hlx-private/p1-spark-morph78-40ep-val-settle-20260924")

def main() -> int:
    os.environ["HYPERLEX_UNBIND_FORCE_TRAIN_PATH"] = str(FORCE)
    bundle = export_dataset(repo_root(), include_live=True)
    rows = [r for r in bundle["rows"] if r.get("task") == "unbind"]
    train = [r for r in rows if r.get("split") == "train"]
    val = [r for r in rows if r.get("split") == "val"]
    _t, val2, force_stats = apply_unbind_force_train(train, val, path=FORCE)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    weight_path = MODEL / "model.safetensors"
    assert weight_path.is_file(), weight_path
    tok = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    enc = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    filler_state, encoder_tensors, heads_blob = _weight_parts(weight_path, torch)
    apply_encoder_trainable(enc, encoder_tensors)
    maps = _load_maps(MODEL, heads_blob)
    hidden = int(getattr(enc.config, "hidden_size", HIDDEN))
    filler_head = _load_filler_head(nn, hidden, filler_state, maps)
    enc.to(device); filler_head.to(device)
    scored = score_unbind_exact(enc, filler_head, tok, maps, val2, device)
    exact = float(scored.get("unbind_exact"))
    n = int(scored.get("n") or scored.get("n_unbind_eval") or 0)
    n_correct = scored.get("n_unbind_exact_correct") or scored.get("n_exact")
    if n_correct is None and n:
        n_correct = round(exact * n)
    hard_n = sum(1 for l in HARD.read_text().splitlines() if l.strip())
    promote = json.loads(PROMOTE.read_text()) if PROMOTE.is_file() else {}
    out = {
        "schema": "hyperlex.fair_eval_same_surface.v0.1",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "model": str(MODEL),
        "seed": "seed-morph65",
        "force_train_path": str(FORCE),
        "force_stats": force_stats,
        "n_hard_atoms": hard_n,
        "unbind_exact": exact,
        "n_scored": n,
        "n_correct_est": n_correct,
        "scored": scored,
        "knob": "fresh civilian acquire-settle highkey shawty + quiet quitting",
        "prior_fair_morph65_n171": 0.9649122807017544,
        "promote": promote,
        "note": "Fair morph65 BEST on morph77 force surface (SoT clean + to_the_moon/elo_hell). Gate morph77 best > this fair + E2 1.0.",
        "fair_exact": exact,
        "fair_n": n,
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    for d in (PRIV, TRAIN_PRIV):
        d.mkdir(parents=True, exist_ok=True)
        (d / OUT.name).write_text(OUT.read_text())
    print(json.dumps({k: out[k] for k in ["unbind_exact","n_scored","n_correct_est","force_stats","knob"]}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
