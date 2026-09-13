"""Head-slot (position-0) filler CE upweight for unbind train.

Default identity (1.0). Morph1 OBSERVED dump: positional_head_filler_miss
dominated civilian misses; morph14 still shows F1≫exact. Scaling only the
first slot CE pushes the head without inventing gold or flipping name_gate.

Env: ``HYPERLEX_UNBIND_HEAD_SLOT_WEIGHT`` — finite float in (0, 4]. Fail closed.
"""

from __future__ import annotations

import math
import os
from typing import Sequence, TypeVar

UNBIND_HEAD_SLOT_WEIGHT_ENV = "HYPERLEX_UNBIND_HEAD_SLOT_WEIGHT"
UNBIND_HEAD_SLOT_WEIGHT_DEFAULT = 1.0
UNBIND_HEAD_SLOT_WEIGHT_MAX = 4.0

_T = TypeVar("_T")


def resolve_unbind_head_slot_weight(raw: str | float | int | None = None) -> float:
    """Identity 1.0. Fail-closed finite in (0, 4]."""
    if raw is None:
        raw = os.environ.get(UNBIND_HEAD_SLOT_WEIGHT_ENV)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return UNBIND_HEAD_SLOT_WEIGHT_DEFAULT
    try:
        weight = float(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{UNBIND_HEAD_SLOT_WEIGHT_ENV} must be a finite number in "
            f"(0, {UNBIND_HEAD_SLOT_WEIGHT_MAX}], got {raw!r}"
        ) from exc
    if not math.isfinite(weight) or weight <= 0 or weight > UNBIND_HEAD_SLOT_WEIGHT_MAX:
        raise ValueError(
            f"{UNBIND_HEAD_SLOT_WEIGHT_ENV} must be a finite number in "
            f"(0, {UNBIND_HEAD_SLOT_WEIGHT_MAX}], got {raw!r}"
        )
    return weight


def apply_head_slot_weight(
    slot_ces: Sequence[_T],
    weight: float,
) -> list[_T]:
    """Scale index-0 CE by ``weight``. Empty → []. Weight 1.0 is a no-op copy."""
    slots = list(slot_ces)
    if not slots:
        return []
    if weight == 1.0:
        return slots
    slots[0] = slots[0] * weight  # type: ignore[operator]
    return slots
