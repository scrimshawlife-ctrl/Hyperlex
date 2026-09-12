"""Spark train loop. Gate only."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .align import atom_token_index, offsets_from_tokenizer, pool_indices
from .export import export_dataset, repo_root, write_export
from .layout import (
    FAMILIES,
    HIDDEN,
    MAX_LEN,
    MODEL_ID_SEED,
    TRUNK,
    UNK,
    describe,
    label_maps,
    resolve_last_trainable,
)
from .save_pretrained import collect_encoder_trainable, save_heads, write_skeleton


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


def freeze_encoder(encoder, last_trainable: int | None = None) -> tuple[int, int]:
    layers = _layers(encoder)
    n_layers = len(list(layers)) if layers is not None else None
    used = resolve_last_trainable(last_trainable, layer_count=n_layers)
    for p in encoder.parameters():
        p.requires_grad = False
    n = 0
    if layers is None:
        return 0, used
    for block in list(layers)[-used:]:
        for p in block.parameters():
            p.requires_grad = True
            n += p.numel()
    return n, used


def _offsets(tok, text: str):
    try:
        return offsets_from_tokenizer(tok, text, max_len=MAX_LEN)
    except TypeError:
        return None


def run_loop(
    trunk: Path,
    out_dir: Path,
    *,
    include_live: bool = False,
    live_store: Path | None = None,
) -> dict:
    root = repo_root()
    bundle = export_dataset(root, include_live=include_live, live_store=live_store)
    write_export(root / "specs" / "007-hyperlexical-model" / "exports", bundle)
    classify_tr = [r for r in bundle["rows"] if r["task"] == "classify" and r["split"] == "train"]
    classify_va = [r for r in bundle["rows"] if r["task"] == "classify" and r["split"] == "val"]
    unbind_tr = [r for r in bundle["rows"] if r["task"] == "unbind" and r["split"] == "train"]
    unbind_va = [r for r in bundle["rows"] if r["task"] == "unbind" and r["split"] == "val"]
    if len(classify_tr) < 8:
        raise RuntimeError("not enough classify train rows")

    import torch
    from torch import nn
    from torch.optim import AdamW

    maps = label_maps(unbind_tr + unbind_va)
    tok, encoder = _require_local_model(trunk)
    hidden = int(getattr(encoder.config, "hidden_size", HIDDEN))
    if hidden != HIDDEN:
        raise RuntimeError(f"hidden {hidden} != {HIDDEN}")
    n_unfrozen, last_trainable_used = freeze_encoder(encoder)
    classify = nn.Linear(hidden, len(FAMILIES))
    role_head = nn.Linear(hidden, len(maps["role_vocab"]))
    filler_head = nn.Linear(hidden, len(maps["filler_vocab"]))
    trainable = [p for p in encoder.parameters() if p.requires_grad] + list(classify.parameters()) + list(role_head.parameters()) + list(filler_head.parameters())
    opt = AdamW(trainable, lr=float(os.environ.get("HYPERLEX_TRAIN_LR", "2e-5")))
    epochs = int(os.environ.get("HYPERLEX_TRAIN_EPOCHS", "2"))
    batch = int(os.environ.get("HYPERLEX_TRAIN_BATCH", "8"))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    for mod in (encoder, classify, role_head, filler_head):
        mod.to(device)
    encoder.train()
    losses = []
    epoch_metrics = []

    def encode_texts(texts):
        enc = tok(texts, padding=True, truncation=True, max_length=MAX_LEN, return_tensors="pt")
        return {k: v.to(device) for k, v in enc.items()}

    def unbind_loss(row):
        fillers = list(row.get("fillers") or [])
        roles = list(row.get("roles") or [])
        if not fillers:
            return None
        out = encoder(**encode_texts([row["text"]]))
        states = out.last_hidden_state[0]
        offs = _offsets(tok, row["text"])
        floss = states.new_zeros(())
        n = 0
        for k, fill in enumerate(fillers):
            idxs = pool_indices(states.size(0), atom_token_index(row["text"], fill, offs))
            h = states[idxs].mean(0)
            gold_f = maps["filler_of"].get(fill, maps["filler_of"][UNK])
            floss = floss + nn.functional.cross_entropy(filler_head(h).unsqueeze(0), torch.tensor([gold_f], device=device))
            n += 1
            if k < len(roles):
                gold_r = maps["role_of"].get(roles[k], maps["role_of"][UNK])
                floss = floss + nn.functional.cross_entropy(role_head(h).unsqueeze(0), torch.tensor([gold_r], device=device))
                n += 1
        return floss / max(1, n)

    @torch.no_grad()
    def score():
        encoder.eval()
        classify.eval()
        filler_head.eval()
        hit = tot = 0
        for row in classify_va or classify_tr[:8]:
            out = encoder(**encode_texts([row["text"]]))
            pred = int(classify(out.last_hidden_state[:, 0]).argmax(-1)[0])
            gold = maps["family_of"].get(row["lineage"], maps["family_of"]["none"])
            hit += int(pred == gold)
            tot += 1
        uhit = utot = 0
        for row in unbind_va or unbind_tr[:8]:
            fillers = list(row.get("fillers") or [])
            if not fillers:
                continue
            out = encoder(**encode_texts([row["text"]]))
            states = out.last_hidden_state[0]
            offs = _offsets(tok, row["text"])
            ok = True
            for k, fill in enumerate(fillers):
                idxs = pool_indices(states.size(0), atom_token_index(row["text"], fill, offs))
                pred = int(filler_head(states[idxs].mean(0)).argmax())
                gold = maps["filler_of"].get(fill, maps["filler_of"][UNK])
                if pred != gold:
                    ok = False
            uhit += int(ok)
            utot += 1
        encoder.train()
        classify.train()
        filler_head.train()
        return {
            "classify_acc": hit / max(1, tot),
            "unbind_exact": uhit / max(1, utot),
            "n_classify_eval": tot,
            "n_unbind_eval": utot,
        }

    for ep in range(epochs):
        for i in range(0, len(classify_tr), batch):
            chunk = classify_tr[i : i + batch]
            y = torch.tensor([maps["family_of"].get(c["lineage"], maps["family_of"]["none"]) for c in chunk], device=device)
            out = encoder(**encode_texts([c["text"] for c in chunk]))
            loss = nn.functional.cross_entropy(classify(out.last_hidden_state[:, 0]), y)
            opt.zero_grad()
            loss.backward()
            opt.step()
            losses.append(float(loss.detach().cpu()))
        for row in unbind_tr:
            uloss = unbind_loss(row)
            if uloss is None:
                continue
            opt.zero_grad()
            uloss.backward()
            opt.step()
            losses.append(float(uloss.detach().cpu()))
        metrics = score()
        metrics["epoch"] = ep
        epoch_metrics.append(metrics)

    out_dir.mkdir(parents=True, exist_ok=True)
    layout = describe(maps)
    layout["last_trainable"] = last_trainable_used
    layout["aligner"] = "char_span + offset_mapping"
    encoder_state = collect_encoder_trainable(encoder)
    state = {
        "classify": classify.state_dict(),
        "role_head": role_head.state_dict(),
        "filler_head": filler_head.state_dict(),
        "encoder": encoder_state,
        "maps": {k: v for k, v in maps.items() if k not in {"family_of", "role_of", "filler_of"}},
        "layout": layout,
    }
    write_skeleton(out_dir, maps=maps)
    weight_file = save_heads(out_dir, state)
    last = epoch_metrics[-1] if epoch_metrics else {}
    receipt = {
        "schema": "hyperlex.hyperlexical.train_receipt.v0.1",
        "model_id": MODEL_ID_SEED,
        "trunk": TRUNK,
        "trunk_dir": str(trunk),
        "device": str(device),
        "cuda": bool(torch.cuda.is_available()),
        "epochs": epochs,
        "n_train_classify": len(classify_tr),
        "n_train_unbind": len(unbind_tr),
        "n_unfrozen_encoder": n_unfrozen,
        "n_encoder_tensors": len(encoder_state),
        "last_trainable": last_trainable_used,
        "last_loss": losses[-1] if losses else None,
        "val": last,
        "epoch_metrics": epoch_metrics,
        "weight_file": weight_file,
        "aligner": "char_span + offset_mapping",
        "data_sha256": bundle["sha256"],
        "include_live": include_live,
        "live_included": bundle["counts"].get("live_included", 0),
        "name_gate": False,
        "e2_pass": False,
        "brier": None,
        "forecast_eligible": False,
        "note": "HF-shaped dump. Not Hyperlexical until E2.",
    }
    (out_dir / "layout.json").write_text(json.dumps(layout, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "train-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "config-train.json").write_text(
        json.dumps(
            {
                "lr": os.environ.get("HYPERLEX_TRAIN_LR", "2e-5"),
                "epochs": epochs,
                "batch": batch,
                "max_len": MAX_LEN,
                "last_trainable": last_trainable_used,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return receipt
