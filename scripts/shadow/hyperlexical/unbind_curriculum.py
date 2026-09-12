"""Scheme-split unbind curriculum. Composes with shape_unbind_train.

Default OFF. Existing trains stay identity (full mix every epoch).
Classify rows are out of scope — this module never sees them.
ne0l0gist harvest / export SoT unchanged. name_gate stays false.
"""

from __future__ import annotations

import os
from typing import Any, Iterable, Mapping

UNBIND_CURRICULUM_ENV = "HYPERLEX_UNBIND_CURRICULUM"
UNBIND_CURRICULUM_POS_EPOCHS_ENV = "HYPERLEX_UNBIND_CURRICULUM_POS_EPOCHS"
UNBIND_CURRICULUM_TYPE_EPOCHS_ENV = "HYPERLEX_UNBIND_CURRICULUM_TYPE_EPOCHS"
UNBIND_CURRICULUM_DEFAULT = 0
# Used only when curriculum is on. Remainder of HYPERLEX_TRAIN_EPOCHS is joint.
UNBIND_CURRICULUM_POS_EPOCHS_DEFAULT = 1
UNBIND_CURRICULUM_TYPE_EPOCHS_DEFAULT = 1

PHASE_POSITIONAL = "positional"
PHASE_TYPE_SLOT = "type_slot"
PHASE_JOINT = "joint"
PHASES = (PHASE_POSITIONAL, PHASE_TYPE_SLOT, PHASE_JOINT)


def resolve_unbind_curriculum(raw: str | int | None = None) -> bool:
    """0|1 gate. Default 0 (off). Fail-closed if invalid."""
    if raw is None:
        raw = os.environ.get(UNBIND_CURRICULUM_ENV)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return False
    token = str(raw).strip()
    if token == "0":
        return False
    if token == "1":
        return True
    raise ValueError(f"{UNBIND_CURRICULUM_ENV} must be 0 or 1, got {raw!r}")


def _resolve_nonneg_int(raw: str | int | None, env_name: str, default: int) -> int:
    if raw is None:
        raw = os.environ.get(env_name)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return default
    try:
        n = int(str(raw).strip(), 10)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{env_name} must be an int >= 0, got {raw!r}") from exc
    if n < 0:
        raise ValueError(f"{env_name} must be an int >= 0, got {n}")
    return n


def resolve_unbind_curriculum_pos_epochs(raw: str | int | None = None) -> int:
    """Positional-first epoch count when curriculum is on. Default 1."""
    return _resolve_nonneg_int(
        raw, UNBIND_CURRICULUM_POS_EPOCHS_ENV, UNBIND_CURRICULUM_POS_EPOCHS_DEFAULT
    )


def resolve_unbind_curriculum_type_epochs(raw: str | int | None = None) -> int:
    """type_slot epoch count when curriculum is on. Default 1."""
    return _resolve_nonneg_int(
        raw, UNBIND_CURRICULUM_TYPE_EPOCHS_ENV, UNBIND_CURRICULUM_TYPE_EPOCHS_DEFAULT
    )


def resolve_curriculum_schedule(
    raw: str | int | None = None,
    *,
    pos_epochs: str | int | None = None,
    type_epochs: str | int | None = None,
) -> dict[str, Any]:
    """Resolved gate + phase lengths. Off → pos/type recorded as 0 (unused)."""
    enabled = resolve_unbind_curriculum(raw)
    if not enabled:
        return {"enabled": False, "pos_epochs": 0, "type_epochs": 0}
    return {
        "enabled": True,
        "pos_epochs": resolve_unbind_curriculum_pos_epochs(pos_epochs),
        "type_epochs": resolve_unbind_curriculum_type_epochs(type_epochs),
    }


def is_type_slot_row(row: Mapping[str, Any]) -> bool:
    return row.get("role_scheme") == PHASE_TYPE_SLOT


def is_positional_phase_row(row: Mapping[str, Any]) -> bool:
    """positional / non-type_slot. TOKEN:/SLOT rows stay in the type_slot bucket."""
    return not is_type_slot_row(row)


def phase_name_for_epoch(epoch: int, schedule: Mapping[str, Any]) -> str:
    if epoch < 0:
        raise ValueError(f"epoch must be >= 0, got {epoch}")
    if not schedule.get("enabled"):
        return PHASE_JOINT
    pos_n = int(schedule.get("pos_epochs") or 0)
    type_n = int(schedule.get("type_epochs") or 0)
    if epoch < pos_n:
        return PHASE_POSITIONAL
    if epoch < pos_n + type_n:
        return PHASE_TYPE_SLOT
    return PHASE_JOINT


def filter_rows_for_phase(rows: Iterable[Mapping[str, Any]], phase: str) -> list[Any]:
    """Exclusive subset. joint = full mix (current behavior)."""
    pool = list(rows)
    if phase == PHASE_JOINT:
        return pool
    if phase == PHASE_TYPE_SLOT:
        return [r for r in pool if is_type_slot_row(r)]
    if phase == PHASE_POSITIONAL:
        return [r for r in pool if is_positional_phase_row(r)]
    raise ValueError(f"unknown unbind curriculum phase {phase!r}")


def select_unbind_for_epoch(
    rows: Iterable[Mapping[str, Any]],
    epoch: int,
    schedule: Mapping[str, Any] | None = None,
) -> tuple[list[Any], dict[str, Any]]:
    """Rows for one epoch. Empty exclusive subset → full mix (fail-closed)."""
    sched = dict(schedule) if schedule is not None else resolve_curriculum_schedule()
    pool = list(rows)
    phase = phase_name_for_epoch(epoch, sched)
    selected = filter_rows_for_phase(pool, phase)
    fallback = False
    if not selected and pool and phase != PHASE_JOINT:
        selected = list(pool)
        fallback = True
    meta = {
        "phase": phase,
        "n_rows": len(selected),
        "fallback_full_mix": fallback,
    }
    return selected, meta


def _clamp_phases(epochs: int, pos_epochs: int, type_epochs: int) -> list[tuple[str, int, int]]:
    """Inclusive-start / exclusive-end epoch ranges actually used."""
    if epochs < 0:
        raise ValueError(f"epochs must be >= 0, got {epochs}")
    pos_end = min(max(0, pos_epochs), epochs)
    type_end = min(max(pos_end, pos_epochs + type_epochs), epochs)
    out: list[tuple[str, int, int]] = []
    if pos_end > 0:
        out.append((PHASE_POSITIONAL, 0, pos_end))
    if type_end > pos_end:
        out.append((PHASE_TYPE_SLOT, pos_end, type_end))
    if epochs > type_end:
        out.append((PHASE_JOINT, type_end, epochs))
    return out


def plan_unbind_curriculum(
    rows: Iterable[Mapping[str, Any]],
    epochs: int,
    schedule: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Receipt-facing phase boundaries + n rows per phase.

    n_rows is the subset that will be trained (after empty-subset fallback).
    """
    sched = dict(schedule) if schedule is not None else resolve_curriculum_schedule()
    pool = list(rows)
    n_pos = sum(1 for r in pool if is_positional_phase_row(r))
    n_type = sum(1 for r in pool if is_type_slot_row(r))
    n_joint = len(pool)
    enabled = bool(sched.get("enabled"))
    pos_n = int(sched.get("pos_epochs") or 0) if enabled else 0
    type_n = int(sched.get("type_epochs") or 0) if enabled else 0
    if not enabled:
        ranges = [(PHASE_JOINT, 0, max(0, epochs))] if epochs > 0 else []
    else:
        ranges = _clamp_phases(epochs, pos_n, type_n)
    phases: list[dict[str, Any]] = []
    for name, start, end in ranges:
        selected = filter_rows_for_phase(pool, name)
        fallback = False
        n_used = len(selected)
        if not selected and pool and name != PHASE_JOINT:
            n_used = n_joint
            fallback = True
        phases.append(
            {
                "name": name,
                "start_epoch": start,
                "end_epoch": end,
                "n_rows": n_used,
                "fallback_full_mix": fallback,
            }
        )
    return {
        "enabled": enabled,
        "pos_epochs": pos_n,
        "type_epochs": type_n,
        "n_unbind_positional": n_pos,
        "n_unbind_type_slot": n_type,
        "n_unbind_joint": n_joint,
        "phases": phases,
    }


def curriculum_env_counts() -> dict[str, int]:
    """Export-facing ints. Does not mutate rows."""
    sched = resolve_curriculum_schedule()
    return {
        "unbind_curriculum": 1 if sched["enabled"] else 0,
        "unbind_curriculum_pos_epochs": int(sched["pos_epochs"]),
        "unbind_curriculum_type_epochs": int(sched["type_epochs"]),
    }
