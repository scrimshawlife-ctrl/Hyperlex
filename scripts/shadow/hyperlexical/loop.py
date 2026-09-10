"""Spark train loop. Gate only. Layout in layout.py."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .export import export_dataset, repo_root, write_export
from .layout import (
    FAMILIES,
    HIDDEN,
    LAST_TRAINABLE,
    MAX_LEN,
    MODEL_ID_SEED,
    TRUNK,
    UNK,
    describe,
    label_maps,
)


def _require_local_model(trunk: Path):
    from transformers import AutoModel, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(str(trunk), local_files_only=True)
    model = AutoModel.from_pretrained(str(trunk), local_files_only=True)
    return tok, model


def _layers(encoder):
    if hasattr(encoder, "layers"):
        return encoder.layers
    inner = getattr(encoder, "encoder", None)
    if inner is not None and hasattr(inner, "layers"):
        return inner.layers
    return None


def freeze_encoder(encoder, last_trainable: int = LAST_TRAINABLE) -> int:
    for p in encoder.parameters():
        p.requires_grad = False
    layers = _layers(encoder)
    n = 0
    if layers is None:
        return 0
    for block in list(layers)[-last_trainable:]:
        for p in block.parameters():
            p.requires_grad = True
            n += p.numel()
    return n


def run_loop(trunk: Path, out_dir: Path) -> dict:
    import torch
    from torch import nn
    from torch.optim import AdamW

    root = repo_root()
    bundle = export_dataset(root)
    write_export(root / "specs" / "007-hyperlexical-model" / "exports", bundle)
    classify_rows = [r for r in bundle["rows"] if r["task"] == "classify" and r["split"] == "train"]
    unbind_rows = [r for r in bundle["rows"] if r["task"] == "unbind" and r["split"] == "train"]
    if len(classify_rows) < 8:
        raise RuntimeError("not enough classify train rows")

    maps = label_maps(unbind_rows)
    tok, encoder = _require_local_model(trunk)
    hidden = int(getattr(encoder.config, "hidden_size", HIDDEN))
    if hidden != HIDDEN:
        raise RuntimeError(f"hidden {hidden} != {HIDDEN}")
    n_unfrozen = freeze_encoder(encoder)
    classify = nn.Linear(hidden, len(FAMILIES))
    role_head = nn.Linear(hidden, len(maps["role_vocab"]))
    filler_head = nn.Linear(hidden, len(maps["filler_vocab"]))
    trainable = [p for p in encoder.parameters() if p.requires_grad] + list(classify.parameters()) + list(role_head.parameters()) + list(filler_head.parameters())
    opt = AdamW(trainable, lr=float(os.environ.get("HYPERLEX_TRAIN_LR", "2e-5")))
    epochs = int(os.environ.get("HYPERLEX_TRAIN_EPOCHS", "2"))
    batch = int(os.environ.get("HYPERLEX_TRAIN_BATCH", "8"))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    encoder.to(device)
    classify.to(device)
    role_head.to(device)
    filler_head.to(device)
    encoder.train()
    losses = []

    def encode_texts(texts):
        enc = tok(texts, padding=True, truncation=True, max_length=MAX_LEN, return_tensors="pt")
        return {k: v.to(device) for k, v in enc.items()}

    for _ in range(epochs):
        for i in range(0, len(classify_rows), batch):
            chunk = classify_rows[i : i + batch]
            y = torch.tensor([maps["family_of"].get(c["lineage"], maps["family_of"]["none"]) for c in chunk], device=device)
            out = encoder(**encode_texts([c["text"] for c in chunk]))
            logits = classify(out.last_hidden_state[:, 0])
            loss = nn.functional.cross_entropy(logits, y)
            opt.zero_grad()
            loss.backward()
            opt.step()
            losses.append(float(loss.detach().cpu()))
        for row in unbind_rows:
            fillers = list(row.get("fillers") or [])
            roles = list(row.get("roles") or [])
            if not fillers:
                continue
            out = encoder(**encode_texts([row["text"]]))
            states = out.last_hidden_state[0]
            seq = states.size(0)
            floss = states.new_zeros(())
            n = 0
            for k, fill in enumerate(fillers):
                idx = min(k + 1, seq - 1)
                h = states[idx]
                gold_f = maps["filler_of"].get(fill, maps["filler_of"][UNK])
                floss = floss + nn.functional.cross_entropy(filler_head(h).unsqueeze(0), torch.tensor([gold_f], device=device))
                n += 1
                if k < len(roles):
                    gold_r = maps["role_of"].get(roles[k], maps["role_of"][UNK])
                    floss = floss + nn.functional.cross_entropy(role_head(h).unsqueeze(0), torch.tensor([gold_r], device=device))
                    n += 1
            if n == 0:
                continue
            opt.zero_grad()
            (floss / n).backward()
            opt.step()
            losses.append(float((floss / n).detach().cpu()))

    out_dir.mkdir(parents=True, exist_ok=True)
    layout = describe(maps)
    torch.save(
        {
            "classify": classify.state_dict(),
            "role_head": role_head.state_dict(),
            "filler_head": filler_head.state_dict(),
            "maps": {k: v for k, v in maps.items() if k not in {"family_of", "role_of", "filler_of"}},
            "layout": layout,
        },
        out_dir / "heads.pt",
    )
    receipt = {
        "schema": "hyperlex.hyperlexical.train_receipt.v0.1",
        "model_id": MODEL_ID_SEED,
        "trunk": TRUNK,
        "trunk_dir": str(trunk),
        "device": str(device),
        "cuda": bool(torch.cuda.is_available()),
        "epochs": epochs,
        "n_train_classify": len(classify_rows),
        "n_train_unbind": len(unbind_rows),
        "n_unfrozen_encoder": n_unfrozen,
        "last_trainable": LAST_TRAINABLE,
        "last_loss": losses[-1] if losses else None,
        "data_sha256": bundle["sha256"],
        "name_gate": False,
        "e2_pass": False,
        "brier": None,
        "forecast_eligible": False,
        "note": "Keepable layout smoke. Not Hyperlexical until E2.",
    }
    (out_dir / "layout.json").write_text(json.dumps(layout, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "train-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "config-train.json").write_text(
        json.dumps({"lr": os.environ.get("HYPERLEX_TRAIN_LR", "2e-5"), "epochs": epochs, "batch": batch, "max_len": MAX_LEN}, indent=2) + "\n",
        encoding="utf-8",
    )
    return receipt
