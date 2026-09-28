"""SELECT-005 reserve census stays deterministic and does not emit a short reserve."""

from __future__ import annotations

import ast
from pathlib import Path

from hyperlexical.select_005_reserve import (
    ADMISSION_FLOORS,
    EXPERIMENT_ID,
    FAILURE_ISOLATION,
    FAILURE_QUOTA,
    PROPOSED_SCHEDULE,
    SELECT_ADMISSION_JSON_SCHEMA_EXISTS,
    TRAINING_AUTHORIZED,
    census,
    exclusion_reason,
    schedule_spec_sha256,
    spent_reserve_hashes,
    unsettled_screen_counts,
    _order_key,
)

MODULE = Path(__file__).resolve().parents[2] / "scripts" / "shadow" / "hyperlexical" / "select_005_reserve.py"


def _event(**overrides):
    row = {
        "class": "OBSERVED",
        "decision": "ACCEPT",
        "lineage": "internet-slang",
        "provenance": "settlement-record",
        "rights": "CC-BY-SA",
        "row_id": "row-1",
        "task": "classify",
        "text_hash": "a" * 64,
    }
    row.update(overrides)
    return row


def _unbind(**overrides):
    return _event(
        row_id="row-u",
        task="unbind",
        text_hash="b" * 64,
        unbind_clean=True,
        lineage="",
        **overrides,
    )


def test_schedule_proposal_is_unsealed_and_does_not_invent_trainer_fields():
    assert PROPOSED_SCHEDULE["sealed"] is False
    assert PROPOSED_SCHEDULE["experiment_id"] == EXPERIMENT_ID
    assert PROPOSED_SCHEDULE["scientific_variable"] == "train_schedule"
    assert PROPOSED_SCHEDULE["selection_metric"] == "classify_macro_f1_nonnone"
    assert PROPOSED_SCHEDULE["baseline"]["HYPERLEX_TRAIN_EPOCHS"] == "40"
    assert PROPOSED_SCHEDULE["candidate"]["HYPERLEX_TRAIN_EPOCHS"] == "12"
    assert PROPOSED_SCHEDULE["candidate"]["HYPERLEX_EARLY_STOP_PATIENCE"] == "4"
    assert PROPOSED_SCHEDULE["candidate"]["HYPERLEX_EARLY_STOP_MIN_EPOCHS"] == "4"
    assert set(PROPOSED_SCHEDULE["unset_fields"]) == {
        "batch_size",
        "gradient_accumulation",
        "learning_rate",
        "seed",
    }
    assert "learning_rate" not in PROPOSED_SCHEDULE
    assert schedule_spec_sha256() == schedule_spec_sha256()
    assert SELECT_ADMISSION_JSON_SCHEMA_EXISTS is False
    assert TRAINING_AUTHORIZED is False
    assert ADMISSION_FLOORS == {
        "classify": 1,
        "classify_observed": 1,
        "classify_non_none": 1,
        "unbind_clean": 1,
    }


def test_blocked_ledger_and_unresolved_rights_are_ineligible():
    spent = {"c" * 64: "EVAL_SPENT"}
    assert exclusion_reason(_event(text_hash="c" * 64), spent, set()) == "EVAL_SPENT"
    assert exclusion_reason(_event(text_hash="d" * 64), {"d" * 64: "TRAIN_CONSUMED"}, set()) == "TRAIN_CONSUMED"
    assert exclusion_reason(_event(decision="UNRESOLVED"), {}, set()) == "DECISION_UNRESOLVED"
    assert exclusion_reason(_event(rights="RIGHTS_UNRESOLVED"), {}, set()) == "RIGHTS_UNRESOLVED"
    assert exclusion_reason(_event(text_hash="e" * 64), {}, {"e" * 64}) == "PINNED_EXPORT"
    assert exclusion_reason(_event(row_id=""), {}, set()) == "PROVENANCE_INCOMPLETE"


def test_two_reconstructions_match_when_the_quota_can_be_filled():
    events = [_event(), _unbind()]
    first = census(events, {}, set())
    second = census(list(reversed(events)), {}, set())
    assert first == second
    assert first["determinism"] == "IDENTICAL"
    assert first["failure"] is None
    assert first["reserve_row_count"] == 2
    assert first["frozen_slice_counts"] == {
        "classify": 1,
        "classify_observed": 1,
        "classify_non_none": 1,
        "unbind_clean": 1,
    }
    assert first["reserve_manifest_sha256"]
    assert first["eligible_order"] == sorted(first["eligible_order"], key=_order_key)


def test_unbind_alone_does_not_freeze_a_partial_reserve():
    report = census([_unbind()], {}, set())
    assert report["failure"] == FAILURE_QUOTA
    assert report["routed_before_freeze_gate"] == 1
    assert report["reserve_row_count"] == 0
    assert report["reserve_manifest_sha256"] is None
    assert report["reserve_rows"] == []
    assert report["training_authorized"] is False


def test_spent_select_rows_cannot_refill_the_quota():
    digest = "a" * 64
    report = census(
        [_event(), _unbind()],
        {digest: "EVAL_SPENT", "b" * 64: "EVAL_SPENT"},
        set(),
    )
    assert report["failure"] == FAILURE_QUOTA
    assert report["eligible_count"] == 0
    assert report["exclusion_counts"]["EVAL_SPENT"] == 2
    assert report["reserve_row_count"] == 0


def test_measurement_overlap_is_an_isolation_failure():
    events = [_event(), _unbind()]
    fences = {
        "threshold_v2_measurement": {
            "hashes": {"b" * 64},
            "row_ids": set(),
            "source_ids": set(),
            "synsets": set(),
        }
    }
    report = census(events, {}, set(), fences=fences)
    assert report["failure"] == FAILURE_ISOLATION
    assert report["reserve_row_count"] == 0
    assert report["reserve_manifest_sha256"] is None
    assert report["isolation"]["threshold_v2_measurement"]["normalized_identity"] == 1


def test_select_004_spent_reserve_is_the_reserved_flag_not_the_binding_list():
    spent = {
        "normalized_text_sha256": "a" * 64,
        "evaluation_spent": True,
        "evaluation_reserved": True,
        "experiment_bindings": [],
    }
    bound_elsewhere = {
        "normalized_text_sha256": "b" * 64,
        "training_consumed": True,
        "experiment_bindings": ["HLX-EXP-2026-09-26-SELECT-001"],
    }
    assert spent_reserve_hashes([spent, bound_elsewhere]) == {"a" * 64}


def test_review_packet_without_a_decision_is_not_a_settlement():
    counts = unsettled_screen_counts(
        [
            {"bucket": "READY_FOR_OPERATOR_REVIEW", "operator_decision": None},
            {"bucket": "RIGHTS_BLOCKED", "operator_decision": ""},
        ]
    )
    assert counts["OPERATOR_DECISION_ABSENT"] == 2
    assert counts["rows"] == 2


def test_module_does_not_train_or_read_the_residual_lane():
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert not any("residual" in name or name.startswith("torch") for name in imported)
    source = MODULE.read_text(encoding="utf-8")
    assert "persist_append" not in source
    assert "optimizer" not in source
