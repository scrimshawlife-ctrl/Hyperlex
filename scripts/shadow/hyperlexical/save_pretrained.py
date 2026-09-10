"""Write a Hub-shaped directory. No network. Weights only if caller passes tensors."""

from __future__ import annotations

import json
from pathlib import Path

from .layout import FAMILIES, HIDDEN, LAST_TRAINABLE, LAYERS, MAX_LEN, MODEL_ID_SEED, TRUNK

CARD_NAME = "hyperlex-encoder-modernbert-base-seed"


def composed_config(maps: dict | None = None) -> dict:
    labels = {str(i): f for i, f in enumerate(FAMILIES)}
    cfg = {
        "model_type": "hyperlex-encoder",
        "architectures": ["HyperlexicalEncoder"],
        "base_model": TRUNK,
        "base_model_relation": "adapter",
        "hidden_size": HIDDEN,
        "num_hidden_layers": LAYERS,
        "last_trainable": LAST_TRAINABLE,
        "max_position_embeddings": MAX_LEN,
        "id2label": labels,
        "label2id": {v: int(k) for k, v in labels.items()},
        "problem_type": "single_label_classification",
        "transformer_tag": "encoder",
        "pipeline_tag": "text-classification",
        "brier": None,
        "name_gate": False,
        "e2_pass": False,
        "model_id": MODEL_ID_SEED,
    }
    if maps:
        cfg["role_vocab"] = maps.get("role_vocab") or []
        cfg["filler_vocab"] = maps.get("filler_vocab") or []
    return cfg


def write_skeleton(out_dir: Path, maps: dict | None = None, card_text: str = "") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = composed_config(maps)
    (out_dir / "config.json").write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if maps:
        (out_dir / "layout.json").write_text(json.dumps({
            "families": maps.get("families"),
            "role_vocab": maps.get("role_vocab"),
            "filler_vocab": maps.get("filler_vocab"),
            "hidden": HIDDEN,
            "last_trainable": LAST_TRAINABLE,
            "aligner": "char_span + offset_mapping",
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if card_text:
        (out_dir / "README.md").write_text(card_text, encoding="utf-8")
    return out_dir


def save_heads(out_dir: Path, state: dict) -> str:
    """Prefer safetensors. Fall back to heads.pt. Caller owns torch."""
    out_dir.mkdir(parents=True, exist_ok=True)
    tensors = {}
    for name in ("classify", "role_head", "filler_head"):
        blob = state.get(name) or {}
        for k, v in blob.items():
            tensors[f"{name}.{k}"] = v
    try:
        from safetensors.torch import save_file

        save_file(tensors, str(out_dir / "model.safetensors"))
        return "model.safetensors"
    except Exception:
        import torch

        torch.save(state, out_dir / "heads.pt")
        return "heads.pt"
