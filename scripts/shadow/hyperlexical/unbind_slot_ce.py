"""Per-slot filler CE as the primary unbind train signal.

Default OFF. Unset env keeps the historical mixed mean (filler CE, role
CE, and morph-margin share one divisor). When armed, mean per-position
filler CE is the primary term; existing list/margin leftovers are
constant-λ additive aux. λ is a fixed receipt constant, not a search.

Civilian unbind_exact stays the ladder metric. Token/slot F1 still emit.
ne0l0gist harvest / export SoT unchanged. name_gate stays false.
"""

from __future__ import annotations

import os
from typing import Any, Sequence, TypeVar

UNBIND_PRIMARY_ENV = "HYPERLEX_UNBIND_PRIMARY"
UNBIND_SLOT_CE_ENV = "HYPERLEX_UNBIND_SLOT_CE"
UNBIND_PRIMARY_MIXED = "mixed"
UNBIND_PRIMARY_SLOT_CE = "slot_ce"
# Fixed aux scale when slot_ce is primary. Not env-overridable.
UNBIND_SLOT_CE_AUX_LAMBDA = 0.25

_T = TypeVar("_T")


def _token_or_none(raw: str | int | None, env_name: str) -> str | None:
    if raw is None:
        raw = os.environ.get(env_name)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    return str(raw).strip()


def _resolve_primary_token(raw: str | None) -> str:
    if raw is None:
        return UNBIND_PRIMARY_MIXED
    if raw in {UNBIND_PRIMARY_MIXED, UNBIND_PRIMARY_SLOT_CE}:
        return raw
    raise ValueError(
        f"{UNBIND_PRIMARY_ENV} must be {UNBIND_PRIMARY_MIXED!r} or "
        f"{UNBIND_PRIMARY_SLOT_CE!r}, got {raw!r}"
    )


def _resolve_slot_ce_flag(raw: str | None) -> bool | None:
    if raw is None:
        return None
    if raw == "0":
        return False
    if raw == "1":
        return True
    raise ValueError(f"{UNBIND_SLOT_CE_ENV} must be 0 or 1, got {raw!r}")


def resolve_unbind_primary_mode(
    primary_raw: str | None = None,
    slot_ce_raw: str | int | None = None,
) -> dict[str, Any]:
    """Resolve primary mode. Default mixed / armed false. Fail-closed.

    Arm with ``HYPERLEX_UNBIND_PRIMARY=slot_ce`` or
    ``HYPERLEX_UNBIND_SLOT_CE=1``. Explicit mixed + SLOT_CE=1, or
    slot_ce + SLOT_CE=0, is a conflict.
    """
    primary_token = _token_or_none(primary_raw, UNBIND_PRIMARY_ENV)
    slot_token = _token_or_none(slot_ce_raw, UNBIND_SLOT_CE_ENV)
    primary = _resolve_primary_token(primary_token)
    slot_flag = _resolve_slot_ce_flag(slot_token)
    if primary == UNBIND_PRIMARY_SLOT_CE and slot_flag is False:
        raise ValueError(
            f"{UNBIND_PRIMARY_ENV}={UNBIND_PRIMARY_SLOT_CE!r} conflicts with "
            f"{UNBIND_SLOT_CE_ENV}=0"
        )
    if primary_token == UNBIND_PRIMARY_MIXED and slot_flag is True:
        raise ValueError(
            f"{UNBIND_PRIMARY_ENV}={UNBIND_PRIMARY_MIXED!r} conflicts with "
            f"{UNBIND_SLOT_CE_ENV}=1"
        )
    armed = primary == UNBIND_PRIMARY_SLOT_CE or slot_flag is True
    mode = UNBIND_PRIMARY_SLOT_CE if armed else UNBIND_PRIMARY_MIXED
    return {
        "unbind_primary": mode,
        "unbind_slot_ce_armed": armed,
        "unbind_slot_ce_aux_lambda": UNBIND_SLOT_CE_AUX_LAMBDA if armed else None,
    }


def _mean(values: Sequence[_T]) -> _T | None:
    if not values:
        return None
    total = values[0]
    for item in values[1:]:
        total = total + item  # type: ignore[operator]
    return total / len(values)  # type: ignore[operator, return-value]


def combine_unbind_train_terms(
    slot_ces: Sequence[_T],
    aux_terms: Sequence[_T],
    *,
    primary: str,
    aux_lambda: float = UNBIND_SLOT_CE_AUX_LAMBDA,
) -> _T | None:
    """Compose per-slot filler CE with list/margin leftovers.

    ``mixed`` (default): mean of slot CE + aux, same divisor the Spark
    loop used before this knob. ``slot_ce``: mean(slot CE) + λ * mean(aux).
    Empty slot list → None (no unbind step). Empty aux → primary only.
    """
    slots = list(slot_ces)
    aux = list(aux_terms)
    if not slots:
        return None
    if primary == UNBIND_PRIMARY_SLOT_CE:
        slot_mean = _mean(slots)
        if slot_mean is None:
            return None
        aux_mean = _mean(aux)
        if aux_mean is None:
            return slot_mean
        return slot_mean + aux_lambda * aux_mean  # type: ignore[operator]
    if primary != UNBIND_PRIMARY_MIXED:
        raise ValueError(
            f"unbind primary must be {UNBIND_PRIMARY_MIXED!r} or "
            f"{UNBIND_PRIMARY_SLOT_CE!r}, got {primary!r}"
        )
    return _mean(slots + aux)
