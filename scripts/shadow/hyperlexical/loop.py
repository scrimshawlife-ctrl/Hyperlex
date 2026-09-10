"""Spark train loop. Imported only after the gate opens."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .export import export_dataset, repo_root, write_export

FAMILIES = [
    "betting-sharp",
    "crypto-degen",
    "ai-native",
    "brainrot-aura",
    "kinship-address",
    "political-status",
    "gaming-meta",
    "workplace-corp",
    "none",
]


def _require_local_model(trunk: Path):
    from transformers import AutoModel, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(str(trunk), local_files_only=True)
    model = AutoModel.from_pretrained(str(trunk), local_files_only=True)
    return tok, model


def run_loop(trunk: Path, out_dir: Path) -> dict:
    import torch
    from torch import nn
    from torch.optim import AdamW

    root = repo_root()
    bundle = export_dataset(root)
    write_export(root / "specs" / "007-hyperlexical-model" / "exports", bundle)
    rows = [r for r in bundle["rows"] if r["task"] == "classify" and r["split"] == "train"]
    if len(rows) < 8:
        raise RuntimeError("not enough classify train rows")

    tok, encoder = _require_local_model(trunk)
    encoder.train()
    label_of = {f: i for i, f in enumerate(FAMILIES)}
    hidden = int(getattr(encoder.config, "hidden_size", 768))
    head = nn.Linear(hidden, len(FAMILIES))
    opt = AdamW(list(encoder.parameters()) + list(head.parameters()), lr=float(os.environ.get("HYPERLEX_TRAIN_LR", "2e-5")))
    epochs = int(os.environ.get("HYPERLEX_TRAIN_EPOCHS", "2"))
    batch = int(os.environ.get("HYPERLEX_TRAIN_BATCH", "8"))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    encoder.to(device)
    head.to(device)
    losses = []
    for _ in range(epochs):
        for i in range(0, len(rows), batch):
            chunk = rows[i : i + batch]
            texts = [c["text"] for c in chunk]
            y = torch.tensor([label_of.get(c["lineage"], label_of["none"]) for c in chunk], device=device)
            enc = tok(texts, padding=True, truncation=True, max_length=64, return_tensors="pt")
            enc = {k: v.to(device) for k, v in enc.items()}
            out = encoder(**enc)
            # pooled path for classify only; unbind must use token states (C29) in a later pass
            pooled = out.last_hidden_state[:, 0]
            logits = head(pooled)
            loss = nn.functional.cross_entropy(logits, y)
            opt.zero_grad()
            loss.backward()
            opt.step()
            losses.append(float(loss.detach().cpu()))
    out_dir.mkdir(parents=True, exist_ok=True)
    torch.save({"head": head.state_dict(), "families": FAMILIES}, out_dir / "heads.pt")
    receipt = {
        "schema": "hyperlex.hyperlexical.train_receipt.v0.1",
        "model_id": "hyperlex-encoder-modernbert-base-seed",
        "trunk": "answerdotai/ModernBERT-base",
        "trunk_dir": str(trunk),
        "device": str(device),
        "cuda": bool(torch.cuda.is_available()),
        "epochs": epochs,
        "n_train_classify": len(rows),
        "last_loss": losses[-1] if losses else None,
        "data_sha256": bundle["sha256"],
        "name_gate": False,
        "e2_pass": False,
        "brier": None,
        "forecast_eligible": False,
        "note": "Seed smoke. Not Hyperlexical. Token-state unbind head not fitted this pass.",
    }
    (out_dir / "train-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "config-train.json").write_text(
        json.dumps(
            {
                "lr": os.environ.get("HYPERLEX_TRAIN_LR", "2e-5"),
                "epochs": epochs,
                "batch": batch,
                "hidden": hidden,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return receipt
