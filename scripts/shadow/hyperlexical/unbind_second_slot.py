"""Second-slot (position-1) filler CE upweight for unbind train.

Default identity (1.0). Morph19 residual: slot-index misses peak at i=1
(119) over head i=0 (82). Head-slot weight=2 already cleared ladder 0.45;
scaling only index-1 pushes the dominant leftover without inventing gold,
flipping name_gate, or uniformly rescaling every slot (which collapses to
unbind_loss_weight).

Env: ``HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT`` — finite float in (0, 4]. Fail closed.
"""

from __future__ import annotations

import math
import os
from typing import Sequence, TypeVar

UNBIND_SECOND_SLOT_WEIGHT_ENV = "HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT"
UNBIND_SECOND_SLOT_WEIGHT_DEFAULT = 1.0
UNBIND_SECOND_SLOT_WEIGHT_MAX = 4.0

_T = TypeVar("_T")


def resolve_unbind_second_slot_weight(raw: str | float | int | None = None) -> float:
    """Identity 1.0. Fail-closed finite in (0, 4]."""
    if raw is None:
        raw = os.environ.get(UNBIND_SECOND_SLOT_WEIGHT_ENV)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return UNBIND_SECOND_SLOT_WEIGHT_DEFAULT
    try:
        weight = float(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{UNBIND_SECOND_SLOT_WEIGHT_ENV} must be a finite number in "
            f"(0, {UNBIND_SECOND_SLOT_WEIGHT_MAX}], got {raw!r}"
        ) from exc
    if not math.isfinite(weight) or weight <= 0 or weight > UNBIND_SECOND_SLOT_WEIGHT_MAX:
        raise ValueError(
            f"{UNBIND_SECOND_SLOT_WEIGHT_ENV} must be a finite number in "
            f"(0, {UNBIND_SECOND_SLOT_WEIGHT_MAX}], got {raw!r}"
        )
    return weight


def apply_second_slot_weight(
    slot_ces: Sequence[_T],
    weight: float,
) -> list[_T]:
    """Scale index-1 CE by ``weight`` when present. Empty/len<2 → copy. Weight 1.0 no-op."""
    slots = list(slot_ces)
    if len(slots) < 2:
        return slots
    if weight == 1.0:
        return slots
    slots[1] = slots[1] * weight  # type: ignore[operator]
    return slots
