"""Trained-model inference for a pinned checkpoint. Lazy torch. Local files only.

Emits ``hyperlex.hyperlexical.inference.v0.1`` with ``MODEL_EMBEDDING``. Lineage
is the classify head on the CLS state, as in train. Unbind treats each
whitespace token as a positional atom and reads role/filler heads on its pooled
token states, as in train val. Brier stays null; this is not a forecast.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from .layout import HIDDEN, MAX_LEN
from .name_gate import PUBLIC_CARD_NAME, name_gate_for, pin_of
from .packet import SCHEMA, build_packet, sha256_hex, validate_packet

WEIGHT_FILE = "model.safetensors"


class InferModelError(RuntimeError):
    pass


def default_trunk_dir() -> Path:
    return Path(
        os.environ.get("HYPERLEX_TRUNK_DIR")
        or Path.home() / ".hyperlex" / "models" / "trunks" / "ModernBERT-base"
    )


def model_identity(model_dir: Path) -> tuple[str, str | None]:
    """(model_id, model_version). Only an approved pin carries the public card name."""
    pin = pin_of(model_dir)
    if name_gate_for(model_dir):
        return PUBLIC_CARD_NAME, pin
    return Path(os.path.realpath(model_dir)).name, pin


def model_packet(
    text: str,
    *,
    model_id: str,
    model_version: str | None,
    vector: list[float],
    param_count: int,
    families: list[str],
    family_probs: list[float],
    atoms: list[dict],
) -> dict:
    """Pure packet assembly from model outputs. No torch."""
    if len(families) != len(family_probs) or not families:
        raise InferModelError("family probabilities do not match families")
    best = max(range(len(families)), key=lambda i: family_probs[i])
    vector_blob = ",".join(f"{v:.6f}" for v in vector).encode("utf-8")
    unbind_ok = bool(atoms) and all(a["filler_pred"] == a["filler"] for a in atoms)
    packet = {
        "schema": SCHEMA,
        "model_id": model_id,
        "model_version": model_version,
        "embed_mode": "MODEL_EMBEDDING",
        "input_hash": sha256_hex(text),
        "vector_hash": hashlib.sha256(vector_blob).hexdigest(),
        "selection_proxy": "unspecified",
        "param_count": int(param_count),
        "surface": text,
        "payload_ref": None,
        "lineage_family": families[best],
        "lineage_confidence": round(float(family_probs[best]), 6),
        "typology": [],
        "stage": None,
        "role_scheme": "positional",
        "unbind_ok": unbind_ok,
        "unbind": {"atoms": atoms},
        "routes_claimed": ["form", "lexical"],
        "restricted_intent_suspected": False,
        "brier": None,
        "forecast_eligible": False,
        "auto_fire": False,
        "class": "INFERRED",
    }
    return validate_packet(packet)


def infer(text: str, *, model_dir: Path, trunk_dir: Path | None = None, restricted: bool = False) -> dict:
    if restricted or "__RESTRICTED_FIXTURE__" in (text or ""):
        return build_packet(text, restricted=True)
    if not (text or "").strip():
        raise InferModelError("empty text")
    model_dir = Path(model_dir)
    trunk_dir = Path(trunk_dir) if trunk_dir else default_trunk_dir()
    weight = model_dir / WEIGHT_FILE
    if not weight.is_file():
        raise InferModelError(f"missing {weight}")
    if not trunk_dir.is_dir():
        raise InferModelError(f"missing trunk snapshot {trunk_dir}")

    from .eval_unbind import TrunkForwardError
    from .eval_forward import _import_torch, _load_maps, _load_trunk, _offsets, apply_encoder_trainable
    from .align import atom_token_index, pool_indices
    from .save_pretrained import split_weight_tensors

    try:
        torch, nn = _import_torch()
        from safetensors.torch import load_file

        split = split_weight_tensors(load_file(str(weight), device="cpu"))
        maps = _load_maps(model_dir, None)
        tok, encoder = _load_trunk(trunk_dir, model_dir)
    except (TrunkForwardError, ImportError) as exc:
        raise InferModelError(str(exc)) from exc
    applied = apply_encoder_trainable(encoder, split["encoder"])
    if applied["present"] and applied["loaded"] == 0:
        raise InferModelError("encoder tensors present but none matched trunk keys")
    heads = {}
    for name, n_out in (
        ("classify", len(maps["families"])),
        ("role_head", len(maps["role_vocab"])),
        ("filler_head", len(maps["filler_vocab"])),
    ):
        state = split.get(name) or {}
        if "weight" not in state or tuple(state["weight"].shape) != (n_out, HIDDEN):
            raise InferModelError(f"{name} shape does not match layout")
        head = nn.Linear(HIDDEN, n_out)
        head.load_state_dict(state)
        heads[name] = head.eval()
    encoder.eval()

    tokens = text.split()
    with torch.no_grad():
        enc = tok([text], truncation=True, max_length=MAX_LEN, return_tensors="pt")
        states = encoder(**enc).last_hidden_state[0]
        cls = states[0]
        probs = torch.softmax(heads["classify"](cls), dim=-1).tolist()
        offs = _offsets(tok, text)
        atoms = []
        for i, token in enumerate(tokens):
            idxs = pool_indices(states.size(0), atom_token_index(text, token, offs))
            h = states[idxs].mean(0)
            role = maps["role_vocab"][int(heads["role_head"](h).argmax())]
            filler = maps["filler_vocab"][int(heads["filler_head"](h).argmax())]
            atoms.append(
                {"role": f"pos_{i}", "role_pred": role, "filler": token.lower(), "filler_pred": filler}
            )
    param_count = sum(p.numel() for p in encoder.parameters()) + sum(
        p.numel() for h in heads.values() for p in h.parameters()
    )
    model_id, model_version = model_identity(model_dir)
    return model_packet(
        text,
        model_id=model_id,
        model_version=model_version,
        vector=cls.tolist(),
        param_count=param_count,
        families=list(maps["families"]),
        family_probs=probs,
        atoms=atoms,
    )
