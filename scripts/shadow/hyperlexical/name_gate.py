"""Which checkpoints may carry the Hyperlexical name. No torch. No network.

The product-level gate is Danny's sentence, recorded as Spec 007 amendment A6.
Only pins listed here are named; every other checkpoint stays ``name_gate=false``.
Identity is the resolved model directory, so a moved ``BEST`` symlink never
names a different checkpoint.
"""

from __future__ import annotations

import os
from pathlib import Path

from .layout import MODEL_ID_SEED

PUBLIC_CARD_NAME = "hyperlex-structure-149m"
APPROVED_PINS = {"seed-morph78": "A6"}


def pin_of(model_dir: str | os.PathLike | None) -> str | None:
    """Return ``seed-<morph>`` for a train-out dir, resolving symlinks, else None."""
    if not model_dir:
        return None
    name = Path(os.path.realpath(model_dir)).name
    prefix = MODEL_ID_SEED + "-"
    if not name.startswith(prefix):
        return None
    return "seed-" + name[len(prefix):]


def name_gate_for(model_dir: str | os.PathLike | None) -> bool:
    return pin_of(model_dir) in APPROVED_PINS
