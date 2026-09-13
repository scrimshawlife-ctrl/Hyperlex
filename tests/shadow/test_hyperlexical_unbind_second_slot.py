"""Spec 007 train knob: second-slot (position-1) filler CE upweight.

Default identity 1.0. Fail-closed in (0, 4]. Does not invent gold.
Civilian unbind_exact stays the ladder metric. name_gate stays false.
"""

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.unbind_head_slot import apply_head_slot_weight
from hyperlexical.unbind_second_slot import (
    UNBIND_SECOND_SLOT_WEIGHT_DEFAULT,
    apply_second_slot_weight,
    resolve_unbind_second_slot_weight,
)
from hyperlexical.unbind_slot_ce import (
    UNBIND_PRIMARY_SLOT_CE,
    combine_unbind_train_terms,
)


def test_resolve_second_slot_default_identity(monkeypatch):
    monkeypatch.delenv("HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT", raising=False)
    assert resolve_unbind_second_slot_weight() == UNBIND_SECOND_SLOT_WEIGHT_DEFAULT == 1.0
    assert resolve_unbind_second_slot_weight("") == 1.0


def test_resolve_second_slot_env_and_explicit(monkeypatch):
    monkeypatch.setenv("HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT", "2")
    assert resolve_unbind_second_slot_weight() == pytest.approx(2.0)
    assert resolve_unbind_second_slot_weight("1.5") == pytest.approx(1.5)
    assert resolve_unbind_second_slot_weight(4) == pytest.approx(4.0)


def test_resolve_second_slot_fail_closed(monkeypatch):
    monkeypatch.delenv("HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT", raising=False)
    for bad in ("0", "-1", "4.1", "nan", "inf", "nope"):
        with pytest.raises(ValueError, match="HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT"):
            resolve_unbind_second_slot_weight(bad)


def test_apply_second_slot_weight_scales_index_one_only():
    assert apply_second_slot_weight([], 2.0) == []
    assert apply_second_slot_weight([9.0], 2.0) == [9.0]
    assert apply_second_slot_weight([1.0, 3.0, 5.0], 1.0) == [1.0, 3.0, 5.0]
    scaled = apply_second_slot_weight([1.0, 3.0, 5.0], 2.0)
    assert scaled[0] == pytest.approx(1.0)
    assert scaled[1] == pytest.approx(6.0)
    assert scaled[2] == pytest.approx(5.0)


def test_second_slot_composes_with_head_slot_and_slot_ce():
    # head=2, second=2 → mean([2, 6]) + 0.25*mean([4]) from [1, 3] + aux 4
    slots = apply_head_slot_weight([1.0, 3.0], 2.0)
    slots = apply_second_slot_weight(slots, 2.0)
    loss = combine_unbind_train_terms(
        slots,
        [4.0],
        primary=UNBIND_PRIMARY_SLOT_CE,
        aux_lambda=0.25,
    )
    assert loss == pytest.approx((2.0 + 6.0) / 2 + 0.25 * 4.0)
