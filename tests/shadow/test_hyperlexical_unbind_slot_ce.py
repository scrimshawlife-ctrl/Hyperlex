"""Spec 007 train knob: per-slot filler CE as primary unbind signal.

Default OFF (mixed mean). Armed mode is mean(slot CE) + fixed-λ aux.
Civilian unbind_exact stays the ladder metric. name_gate stays false.
"""

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.unbind_slot_ce import (
    UNBIND_PRIMARY_MIXED,
    UNBIND_PRIMARY_SLOT_CE,
    UNBIND_SLOT_CE_AUX_LAMBDA,
    combine_unbind_train_terms,
    resolve_unbind_primary_mode,
)


def _clear_slot_ce_env(monkeypatch):
    monkeypatch.delenv("HYPERLEX_UNBIND_PRIMARY", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_SLOT_CE", raising=False)


def test_resolve_primary_default_off(monkeypatch):
    _clear_slot_ce_env(monkeypatch)
    mode = resolve_unbind_primary_mode()
    assert mode["unbind_primary"] == UNBIND_PRIMARY_MIXED
    assert mode["unbind_slot_ce_armed"] is False
    assert mode["unbind_slot_ce_aux_lambda"] is None
    assert resolve_unbind_primary_mode("", "")["unbind_slot_ce_armed"] is False
    assert resolve_unbind_primary_mode("  ", "  ")["unbind_slot_ce_armed"] is False


def test_resolve_primary_slot_ce_env(monkeypatch):
    _clear_slot_ce_env(monkeypatch)
    monkeypatch.setenv("HYPERLEX_UNBIND_PRIMARY", "slot_ce")
    mode = resolve_unbind_primary_mode()
    assert mode["unbind_primary"] == UNBIND_PRIMARY_SLOT_CE
    assert mode["unbind_slot_ce_armed"] is True
    assert mode["unbind_slot_ce_aux_lambda"] == UNBIND_SLOT_CE_AUX_LAMBDA == 0.25


def test_resolve_slot_ce_flag_alias(monkeypatch):
    _clear_slot_ce_env(monkeypatch)
    monkeypatch.setenv("HYPERLEX_UNBIND_SLOT_CE", "1")
    mode = resolve_unbind_primary_mode()
    assert mode["unbind_primary"] == UNBIND_PRIMARY_SLOT_CE
    assert mode["unbind_slot_ce_armed"] is True
    assert mode["unbind_slot_ce_aux_lambda"] == pytest.approx(0.25)
    _clear_slot_ce_env(monkeypatch)
    monkeypatch.setenv("HYPERLEX_UNBIND_SLOT_CE", "0")
    off = resolve_unbind_primary_mode()
    assert off["unbind_slot_ce_armed"] is False
    assert off["unbind_primary"] == UNBIND_PRIMARY_MIXED


def test_resolve_explicit_mixed_and_agreeing_flags(monkeypatch):
    _clear_slot_ce_env(monkeypatch)
    mixed = resolve_unbind_primary_mode("mixed", "0")
    assert mixed["unbind_slot_ce_armed"] is False
    both = resolve_unbind_primary_mode("slot_ce", "1")
    assert both["unbind_slot_ce_armed"] is True
    assert both["unbind_primary"] == UNBIND_PRIMARY_SLOT_CE


def test_resolve_primary_rejects_invalid_and_conflicts(monkeypatch):
    _clear_slot_ce_env(monkeypatch)
    monkeypatch.setenv("HYPERLEX_UNBIND_PRIMARY", "isa")
    with pytest.raises(ValueError, match="mixed"):
        resolve_unbind_primary_mode()
    monkeypatch.setenv("HYPERLEX_UNBIND_PRIMARY", "slot_ce")
    monkeypatch.setenv("HYPERLEX_UNBIND_SLOT_CE", "0")
    with pytest.raises(ValueError, match="conflicts"):
        resolve_unbind_primary_mode()
    monkeypatch.setenv("HYPERLEX_UNBIND_PRIMARY", "mixed")
    monkeypatch.setenv("HYPERLEX_UNBIND_SLOT_CE", "1")
    with pytest.raises(ValueError, match="conflicts"):
        resolve_unbind_primary_mode()
    _clear_slot_ce_env(monkeypatch)
    monkeypatch.setenv("HYPERLEX_UNBIND_SLOT_CE", "true")
    with pytest.raises(ValueError, match="must be 0 or 1"):
        resolve_unbind_primary_mode()
    monkeypatch.setenv("HYPERLEX_UNBIND_SLOT_CE", "2")
    with pytest.raises(ValueError, match="must be 0 or 1"):
        resolve_unbind_primary_mode()


def test_aux_lambda_is_fixed_not_an_env_search(monkeypatch):
    _clear_slot_ce_env(monkeypatch)
    monkeypatch.setenv("HYPERLEX_UNBIND_SLOT_CE_LAMBDA", "0.9")
    monkeypatch.setenv("HYPERLEX_UNBIND_PRIMARY", "slot_ce")
    mode = resolve_unbind_primary_mode()
    assert mode["unbind_slot_ce_aux_lambda"] == 0.25
    assert UNBIND_SLOT_CE_AUX_LAMBDA == 0.25


def test_combine_mixed_matches_historical_mean():
    # Two slot CEs + one margin + one role, same divisor as the old loop.
    mixed = combine_unbind_train_terms(
        [1.0, 3.0],
        [2.0, 6.0],
        primary=UNBIND_PRIMARY_MIXED,
    )
    assert mixed == pytest.approx((1.0 + 3.0 + 2.0 + 6.0) / 4)
    slots_only = combine_unbind_train_terms(
        [1.0, 3.0],
        [],
        primary=UNBIND_PRIMARY_MIXED,
    )
    assert slots_only == pytest.approx(2.0)


def test_combine_slot_ce_primary_plus_fixed_aux():
    # mean(slot) + 0.25 * mean(aux)
    armed = combine_unbind_train_terms(
        [1.0, 3.0],
        [2.0, 6.0],
        primary=UNBIND_PRIMARY_SLOT_CE,
        aux_lambda=UNBIND_SLOT_CE_AUX_LAMBDA,
    )
    assert armed == pytest.approx(2.0 + 0.25 * 4.0)
    no_aux = combine_unbind_train_terms(
        [1.0, 3.0],
        [],
        primary=UNBIND_PRIMARY_SLOT_CE,
    )
    assert no_aux == pytest.approx(2.0)


def test_combine_empty_slots_is_none():
    assert (
        combine_unbind_train_terms([], [1.0], primary=UNBIND_PRIMARY_MIXED) is None
    )
    assert (
        combine_unbind_train_terms([], [1.0], primary=UNBIND_PRIMARY_SLOT_CE) is None
    )


def test_combine_rejects_unknown_primary():
    with pytest.raises(ValueError, match="unbind primary"):
        combine_unbind_train_terms([1.0], [], primary="list_exact")


def test_slot_ce_primary_does_not_dilute_ce_with_margin():
    """Near-miss regime: F1 ≫ exact. Margin must not share the CE divisor."""
    slots = [0.2, 0.4, 0.6]
    aux = [8.0, 8.0, 8.0]
    mixed = combine_unbind_train_terms(slots, aux, primary=UNBIND_PRIMARY_MIXED)
    armed = combine_unbind_train_terms(
        slots, aux, primary=UNBIND_PRIMARY_SLOT_CE, aux_lambda=0.25
    )
    assert mixed == pytest.approx((0.2 + 0.4 + 0.6 + 24.0) / 6)
    assert armed == pytest.approx(0.4 + 0.25 * 8.0)
    assert armed < mixed
