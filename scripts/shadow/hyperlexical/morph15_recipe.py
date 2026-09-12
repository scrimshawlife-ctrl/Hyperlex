"""Torch-free morph15 recipe preflight.

Resolves Spec 007 unbind env knobs the Spark morph15 card arms, without
loading ModernBERT or CUDA. Fail-closed on invalid values. name_gate stays
false. Does not invent OBSERVED gold.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .unbind_curriculum import (
    resolve_unbind_curriculum,
    resolve_unbind_curriculum_pos_epochs,
    resolve_unbind_curriculum_type_epochs,
)
from .unbind_head_slot import resolve_unbind_head_slot_weight
from .unbind_recipe import (
    resolve_unbind_hard_atoms_path,
    resolve_unbind_hard_upsample,
    resolve_unbind_inferred_weight,
    resolve_unbind_observed_upsample,
)
from .unbind_residual import resolve_unbind_residual_dump_path
from .unbind_slot_ce import resolve_unbind_primary_mode  # armed via HYPERLEX_UNBIND_PRIMARY


def morph15_recipe_snapshot() -> dict:
    """Effective morph15 card values. Raises ValueError on bad env."""
    primary = resolve_unbind_primary_mode()
    hard_path = resolve_unbind_hard_atoms_path()
    residual = resolve_unbind_residual_dump_path()
    return {
        "schema": "hyperlex.hyperlexical.morph15_recipe.v0.1",
        "unbind_primary": primary["unbind_primary"],
        "unbind_slot_ce_armed": primary["unbind_slot_ce_armed"],
        "unbind_slot_ce_aux_lambda": primary["unbind_slot_ce_aux_lambda"],
        "unbind_observed_upsample": resolve_unbind_observed_upsample(),
        "unbind_inferred_weight": resolve_unbind_inferred_weight(),
        "unbind_curriculum": resolve_unbind_curriculum(),
        "unbind_curriculum_pos_epochs": resolve_unbind_curriculum_pos_epochs(),
        "unbind_curriculum_type_epochs": resolve_unbind_curriculum_type_epochs(),
        "unbind_hard_atoms_path": hard_path,
        "unbind_hard_atoms_exists": bool(hard_path and Path(hard_path).is_file()),
        "unbind_hard_upsample": resolve_unbind_hard_upsample(),
        "unbind_head_slot_weight": resolve_unbind_head_slot_weight(),
        "unbind_residual_dump": residual,
        "include_live": os.environ.get("HYPERLEX_INCLUDE_LIVE") == "1",
        "train_epochs": int(os.environ.get("HYPERLEX_TRAIN_EPOCHS") or "0") or None,
        "train_out": os.environ.get("HYPERLEX_TRAIN_OUT") or "",
        "name_gate": False,
        "ladder_unbind_exact": [0.45, 0.55, 0.65],
        "pin_best": "seed-morph14",
        "note": "Recipe resolve only. Not a train. Not E2. Not Hyperlexical-named.",
    }


def main(argv: list[str] | None = None) -> int:
    del argv  # unused — env is the contract
    try:
        snap = morph15_recipe_snapshot()
    except ValueError as exc:
        print(json.dumps({"abort": True, "error": str(exc), "name_gate": False}, indent=2))
        return 2
    print(json.dumps(snap, indent=2, sort_keys=True))
    # Soft warn: morph15 card expects hard atoms on Spark
    if snap["unbind_hard_upsample"] > 1 and not snap["unbind_hard_atoms_exists"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
