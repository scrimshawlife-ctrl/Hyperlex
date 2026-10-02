"""Deterministic representation for Hyperlex Instrument V1."""

from __future__ import annotations

import hashlib
import math
import struct
from typing import Any

from .constants import (
    ENCODER_ID,
    ENCODER_PIN_PREIMAGE,
    ENCODER_REVISION,
    ENCODER_ROLE,
    STATIC_EMBED_DIMS,
)


def encoder_pin_hash() -> str:
    return hashlib.sha256(ENCODER_PIN_PREIMAGE.encode("utf-8")).hexdigest()


def static_hash_embedding(text: str, *, dims: int = STATIC_EMBED_DIMS) -> list[float]:
    """Stable unit-ish embedding from text bytes (no model download)."""
    raw = (text or "").encode("utf-8")
    vec: list[float] = []
    for i in range(dims):
        digest = hashlib.sha256(raw + struct.pack(">I", i)).digest()
        # Map first 4 bytes to [-1, 1]
        unsigned = int.from_bytes(digest[:4], "big")
        vec.append((unsigned / 0xFFFFFFFF) * 2.0 - 1.0)
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [round(v / norm, 8) for v in vec]


def build_representation(text: str) -> dict[str, Any]:
    """Always emit STATIC_HASH_EMBEDDING; model path remains optional/unavailable."""
    emb = static_hash_embedding(text)
    emb_bytes = struct.pack(f">{len(emb)}d", *emb)
    emb_ref = hashlib.sha256(emb_bytes).hexdigest()
    return {
        "encoder_id": ENCODER_ID,
        "encoder_hash": encoder_pin_hash(),
        "encoder_revision": ENCODER_REVISION,
        "encoder_role": ENCODER_ROLE,
        "embed_mode": "STATIC_HASH_EMBEDDING",
        "embedding": emb,
        "embedding_ref": emb_ref,
        "dims": len(emb),
        "model_embedding_available": False,
        "note": (
            "Offline deterministic representation. Frozen MSMARCO pin is the "
            "settled family identity; weight load is optional and not required "
            "for SHADOW_INSTRUMENT_ONLY."
        ),
    }
