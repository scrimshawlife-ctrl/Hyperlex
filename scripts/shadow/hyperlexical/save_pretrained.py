"""Write a Hub-shaped directory. No network. Weights only if caller passes tensors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .layout import FAMILIES, HIDDEN, LAST_TRAINABLE, LAYERS, MAX_LEN, MODEL_ID_SEED, TRUNK

CARD_NAME = "hyperlex-encoder-modernbert-base-seed"
ENCODER_PREFIX = "encoder."
FACTORIZED_HEAD_NAMES = (
    "relation_head",
    "resolvability_head",
)
_HEAD_NAMES = (
    "classify",
    "role_head",
    "filler_head",
    "applicability",
    "family_head",
    "evidence_head",
    "gate1_head",
    "gate2_head",
    # Factorized Stage-A heads (must be present for promote/cold-load).
    *FACTORIZED_HEAD_NAMES,
)

# Canonical Stage-A factorized head shapes: Linear(HIDDEN, 2).
FACTORIZED_HEAD_WEIGHT_SHAPE = (2, HIDDEN)
FACTORIZED_HEAD_BIAS_SHAPE = (2,)


def encoder_tensor_key(name: str) -> str:
    if name.startswith(ENCODER_PREFIX):
        return name
    return f"{ENCODER_PREFIX}{name}"


def flatten_weight_tensors(state: dict) -> dict:
    """Heads plus trainable encoder tensors. Encoder keys are encoder.<hf_path>."""
    tensors = {}
    for name in _HEAD_NAMES:
        blob = state.get(name) or {}
        if not isinstance(blob, dict):
            continue
        for key, value in blob.items():
            tensors[f"{name}.{key}"] = value
    encoder = state.get("encoder") or {}
    if isinstance(encoder, dict):
        for key, value in encoder.items():
            tensors[encoder_tensor_key(str(key))] = value
    return tensors


def _tensor_shape(value: Any) -> tuple[int, ...] | None:
    if value is None:
        return None
    shape = getattr(value, "shape", None)
    if shape is not None:
        try:
            return tuple(int(x) for x in shape)
        except Exception:
            return None
    if isinstance(value, (list, tuple)):
        if not value:
            return (0,)
        if isinstance(value[0], (list, tuple)):
            return (len(value), len(value[0]))
        return (len(value),)
    return None


def require_factorized_heads_in_flat(tensors: Mapping[str, Any]) -> dict[str, Any]:
    """Fail-closed check that factorized Stage-A heads survived flatten/save."""
    keys = set(str(k) for k in tensors.keys())
    required = [
        f"{name}.{suffix}"
        for name in FACTORIZED_HEAD_NAMES
        for suffix in ("weight", "bias")
    ]
    missing = [key for key in required if key not in keys]
    shape_errors = []
    for name in FACTORIZED_HEAD_NAMES:
        weight_key = f"{name}.weight"
        bias_key = f"{name}.bias"
        if weight_key in tensors:
            shape = _tensor_shape(tensors[weight_key])
            if shape is not None and shape != FACTORIZED_HEAD_WEIGHT_SHAPE:
                shape_errors.append(
                    {
                        "tensor": weight_key,
                        "observed": list(shape),
                        "expected": list(FACTORIZED_HEAD_WEIGHT_SHAPE),
                    }
                )
        if bias_key in tensors:
            shape = _tensor_shape(tensors[bias_key])
            if shape is not None and shape != FACTORIZED_HEAD_BIAS_SHAPE:
                shape_errors.append(
                    {
                        "tensor": bias_key,
                        "observed": list(shape),
                        "expected": list(FACTORIZED_HEAD_BIAS_SHAPE),
                    }
                )
    return {
        "pass": not missing and not shape_errors,
        "missing": missing,
        "present": [key for key in required if key in keys],
        "required": required,
        "shape_errors": shape_errors,
        "factorized_head_names": list(FACTORIZED_HEAD_NAMES),
    }


def assert_factorized_heads_in_flat(tensors: Mapping[str, Any]) -> dict[str, Any]:
    """Raise if flatten/save dropped or misshaped factorized heads."""
    report = require_factorized_heads_in_flat(tensors)
    if report["pass"]:
        return report
    parts = []
    if report["missing"]:
        parts.append(f"missing={report['missing']}")
    if report["shape_errors"]:
        parts.append(f"shape_errors={report['shape_errors']}")
    raise ValueError(f"factorized_heads_invalid:{';'.join(parts)}")


def split_weight_tensors(tensors: dict) -> dict:
    """Inverse of flatten_weight_tensors. Encoder map keeps the encoder. prefix."""
    out = {name: {} for name in _HEAD_NAMES}
    out["encoder"] = {}
    for key, value in tensors.items():
        if key.startswith(ENCODER_PREFIX):
            out["encoder"][key] = value
            continue
        prefix, _, rest = key.partition(".")
        if prefix in _HEAD_NAMES and rest:
            out[prefix][rest] = value
    return out


def collect_encoder_trainable(encoder) -> dict:
    """requires_grad encoder params. Keys: encoder.<hf named_parameters path>."""
    named = getattr(encoder, "named_parameters", None)
    if named is None:
        return {}
    out = {}
    for name, param in named():
        if not getattr(param, "requires_grad", False):
            continue
        tensor = param.detach()
        to_cpu = getattr(tensor, "cpu", None)
        if callable(to_cpu):
            tensor = to_cpu()
        contiguous = getattr(tensor, "contiguous", None)
        if callable(contiguous):
            tensor = contiguous()
        out[encoder_tensor_key(name)] = tensor
    return out


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
    tensors = flatten_weight_tensors(state)
    try:
        from safetensors.torch import save_file

        save_file(tensors, str(out_dir / "model.safetensors"))
        return "model.safetensors"
    except Exception:
        import torch

        torch.save(state, out_dir / "heads.pt")
        return "heads.pt"
