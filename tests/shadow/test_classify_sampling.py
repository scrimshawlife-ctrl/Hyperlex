"""SELECT-007 sampling rule. No training."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classify_sampling import (  # noqa: E402
    CAP,
    RULE,
    apply_inferred_none_cap,
    epoch_classify_rows,
    parse_sampling_policy,
)


def _row(text: str, lineage: str, evidence: str, **extra: object) -> dict:
    row = {"class": evidence, "lineage": lineage, "text": text}
    row.update(extra)
    return row


def _population() -> list[dict]:
    rows = [_row(f"other-{index}", "gaming-meta", "OBSERVED") for index in range(4)]
    rows.append(_row("obs-none", "none", "OBSERVED"))
    rows.extend(_row(f"inf-{index}", "none", "INFERRED", loss=index / 10) for index in range(6))
    return rows


def test_unset_policy_keeps_every_row_in_order():
    rows = _population()
    kept, record = epoch_classify_rows(rows, epoch_index=0, policy=None)
    assert [row["text"] for row in kept] == [row["text"] for row in rows]
    assert record["rule"] == "uncapped"
    assert record["inferred_none_selected"] == 6
    assert record["observed_none"] == 1


def test_parser_accepts_only_the_frozen_cap():
    assert parse_sampling_policy(None) == ("uncapped", None)
    assert parse_sampling_policy("uncapped") == ("uncapped", None)
    assert parse_sampling_policy(f"{RULE}:{CAP}") == (RULE, CAP)
    with pytest.raises(ValueError):
        parse_sampling_policy(f"{RULE}:218")
    with pytest.raises(ValueError):
        parse_sampling_policy("loss-weighted")


def test_cap_preserves_non_none_and_observed_none_order():
    rows = _population()
    kept, record = apply_inferred_none_cap(rows, epoch_index=0, cap=2)
    texts = [row["text"] for row in kept]
    assert texts[:4] == [f"other-{index}" for index in range(4)]
    assert "obs-none" in texts
    assert sum(row["lineage"] != "none" for row in kept) == 4
    assert sum(row["class"] == "OBSERVED" and row["lineage"] == "none" for row in kept) == 1
    assert record["inferred_none_selected"] == 2
    assert len(record["selected_identity_sha256"]) == 2


def test_cap_is_deterministic_and_ignores_loss():
    rows = _population()
    other = _population()
    for row in other:
        row["loss"] = 99
        row["prediction"] = "none"
    first, first_record = apply_inferred_none_cap(rows, epoch_index=1, cap=3)
    second, second_record = apply_inferred_none_cap(other, epoch_index=1, cap=3)
    assert [row["text"] for row in first] == [row["text"] for row in second]
    assert first_record["selected_identity_sha256"] == second_record["selected_identity_sha256"]
    assert first_record["selection_sha256"] == second_record["selection_sha256"]


def test_epochs_rotate_and_do_not_shrink_other_classes():
    rows = _population()
    epoch0, record0 = apply_inferred_none_cap(rows, epoch_index=0, cap=2)
    epoch1, record1 = apply_inferred_none_cap(rows, epoch_index=1, cap=2)
    assert record0["selected_identity_sha256"] != record1["selected_identity_sha256"]
    assert [row["text"] for row in epoch0 if row["lineage"] != "none"] == [
        row["text"] for row in epoch1 if row["lineage"] != "none"
    ]


def test_production_cap_refuses_a_different_population():
    with pytest.raises(ValueError, match="preregistered"):
        epoch_classify_rows(_population(), epoch_index=0, policy=f"{RULE}:{CAP}")
