"""SELECT-005 supply review does not promote inferred rows or seal missing numbers."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from hyperlexical.select_005_supply import (
    EXCLUDED_BUCKETS,
    PREREGISTRATION_INCOMPLETE,
    THRESHOLDS_BLOCKED,
    THRESHOLD_AUTHORIZATION_JSON_SCHEMA_EXISTS,
    UNRESOLVED_SCHEDULE_FIELDS,
    extract_review_ready,
    manifest_jsonl,
    manifest_record,
    preregistration_status,
    refuse_observed_promotion,
    settlement_refusal,
    threshold_authorization_proposal,
    validate_operator_decision,
)

MODULE = Path(__file__).resolve().parents[2] / "scripts" / "shadow" / "hyperlexical" / "select_005_supply.py"


def _row(bucket, candidate_id="c1", text="alpha"):
    return {
        "bucket": bucket,
        "candidate_id": candidate_id,
        "canonical text": text,
        "rights basis": "MIT-examples",
        "source": "export.jsonl",
        "source locator": "line:1",
    }


def test_review_ready_extraction_drops_blocked_rows_and_is_stable():
    rows = [
        _row("RIGHTS_BLOCKED", "r"),
        _row("READY_FOR_OPERATOR_REVIEW", "a", "one"),
        _row("PROVENANCE_BLOCKED", "p"),
        _row("READY_FOR_OPERATOR_REVIEW", "b", "two"),
        _row("DUPLICATE_OR_OVERLAP", "d"),
    ]
    first = extract_review_ready(rows)
    second = extract_review_ready(list(rows))
    assert [row["candidate_id"] for row in first] == ["a", "b"]
    assert manifest_jsonl(
        [
            manifest_record(
                row,
                normalized_identity="ab",
                source_class="INFERRED",
                source_provenance="LINEAGE_REGISTRY:ai-native",
                existing_settlement_state="ABSENT",
            )
            for row in first
        ]
    ) == manifest_jsonl(
        [
            manifest_record(
                row,
                normalized_identity="ab",
                source_class="INFERRED",
                source_provenance="LINEAGE_REGISTRY:ai-native",
                existing_settlement_state="ABSENT",
            )
            for row in second
        ]
    )
    assert "quota" not in manifest_jsonl(
        [
            manifest_record(
                first[0],
                normalized_identity="ab",
                source_class="INFERRED",
                source_provenance="LINEAGE_REGISTRY:ai-native",
                existing_settlement_state="ABSENT",
            )
        ]
    )
    assert EXCLUDED_BUCKETS == {"RIGHTS_BLOCKED", "PROVENANCE_BLOCKED", "DUPLICATE_OR_OVERLAP"}


def test_inferred_registry_class_is_not_promoted_to_observed():
    with pytest.raises(SystemExit, match="not promoted to OBSERVED"):
        refuse_observed_promotion("INFERRED", "OBSERVED")
    validate_operator_decision(
        {
            "attest": "INFERRED",
            "decision": "ACCEPT",
            "rights": "MIT-examples",
            "semantic_family": "ai-native",
            "source_rights": "MIT-examples",
        },
        source_class="INFERRED",
    )
    with pytest.raises(SystemExit, match="rights state was changed"):
        validate_operator_decision(
            {
                "attest": "INFERRED",
                "decision": "ACCEPT",
                "rights": "CC-BY-SA",
                "semantic_family": "ai-native",
                "source_rights": "MIT-examples",
            },
            source_class="INFERRED",
        )


def test_settlement_apply_refuses_rows_outside_the_held_out_stream():
    message = settlement_refusal(
        [{"row_id": "HLX-CAND-not-in-stream", "decision": "UNRESOLVED"}],
        [{"row_key": "hs-existing", "text": "other", "source_type": "wiktionary_category"}],
    )
    assert "not in the held-out stream" in message


def test_preregistration_stays_incomplete_without_inheriting_select_004():
    status = preregistration_status()
    assert status["state"] == PREREGISTRATION_INCOMPLETE
    assert status["sealed"] is False
    assert status["inherited_select_004_hyperparameters"] is False
    assert status["unresolved_fields"] == list(UNRESOLVED_SCHEDULE_FIELDS)
    assert "2e-5" not in str(status["resolved_schedule"])


def test_threshold_proposal_does_not_seal_numeric_floors():
    proposal = threshold_authorization_proposal()
    assert proposal["sealed"] is False
    assert proposal["state"] == THRESHOLDS_BLOCKED
    assert proposal["decision_thresholds"] == {}
    assert proposal["inherited_from_select_004"] is False
    assert THRESHOLD_AUTHORIZATION_JSON_SCHEMA_EXISTS is True
    assert all(item["numeric_threshold"] is None for item in proposal["metrics"])
    assert [item["metric"] for item in proposal["metrics"]] == [
        "classify_macro_f1_nonnone",
        "classification_accuracy",
        "observed_label_accuracy",
        "unbind_clean_exact",
    ]


def test_module_does_not_touch_the_residual_lane_or_commit_settlements():
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not any("residual" in name for name in imported)
    assert "commit_settlement" not in source
    assert "persist_append" not in source
