"""Retrospective schemas check sealed residual-threshold artifacts without rewriting them."""

from __future__ import annotations

import inspect

import pytest
from jsonschema import Draft202012Validator

from hyperlexical import residual_threshold_schema as schema_mod
from hyperlexical.residual_threshold_schema import (
    GAP,
    PASS,
    SOURCE,
    classify,
    conformance_report,
    evidence_hashes,
    load_schemas,
    schema_registry,
)


def _validator(schema: dict, registry):
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=registry)


def _schemas():
    loaded = load_schemas()
    return loaded, schema_registry(loaded)


def _completion(**overrides) -> dict:
    document = {
        "calibration_redraw": False,
        "confound_gate": "PASS",
        "direction_gate": "SUPPORTED_DIRECTION",
        "json_schema_document": None,
        "json_schema_exists": False,
        "measurement_eligible": False,
        "measurement_state": "SEALED",
        "operator_labeling": "LABELS_FROZEN",
        "runtime_integration": False,
        "select_005_authorized": False,
        "selected_source": "none",
        "support_gate": "SUPPORT_GATE_PASSED",
        "surface_draw": "SURFACES_FROZEN",
        "threshold_frozen": False,
        "threshold_search": "NO_THRESHOLD_PASSES_PRECISION_GATE",
        "threshold_value": None,
        "training_authorized": False,
        "training_readiness": "BLOCKED_BY_THRESHOLD_V2_CALIBRATION",
    }
    document.update(overrides)
    return document


def _join(**overrides) -> dict:
    row = {
        "calibration_row_id": 1,
        "operator_label": "HIGH",
        "pos": "noun",
        "pwn30_synset": "noun:01234567",
        "residual_score": "0.1000000000",
        "row_id": "a" * 64,
        "row_resolution_status": "RESIDUAL_READY",
        "surface": "example phrase",
    }
    row.update(overrides)
    return row


def test_schema_family_is_draft_2020_12():
    loaded, _registry = _schemas()
    assert set(loaded) == {
        "residual-threshold-common.schema.json",
        "residual-threshold-completion-receipt.schema.json",
        "residual-threshold-confound-analysis.schema.json",
        "residual-threshold-decision.schema.json",
        "residual-threshold-direction-analysis.schema.json",
        "residual-threshold-receipt.schema.json",
        "residual-threshold-support-join.schema.json",
        "residual-threshold-surface-manifest.schema.json",
        "residual-threshold-threshold-search.schema.json",
    }
    for document in loaded.values():
        Draft202012Validator.check_schema(document)


def test_completion_receipt_is_not_a_generic_receipt():
    assert classify("RESIDUAL_THRESHOLD_V2_CALIBRATION_COMPLETION_RECEIPT.json") == "completion"
    assert classify("RESIDUAL_THRESHOLD_V2_SURFACE_DRAW_RECEIPT.json") == "receipt"


def test_unfrozen_threshold_requires_null_value():
    loaded, registry = _schemas()
    validator = _validator(loaded["residual-threshold-completion-receipt.schema.json"], registry)
    assert not validator.is_valid(_completion(threshold_value="0.2500000000"))
    assert validator.is_valid(_completion())


def test_frozen_threshold_requires_numeric_value_and_metrics():
    loaded, registry = _schemas()
    validator = _validator(loaded["residual-threshold-completion-receipt.schema.json"], registry)
    frozen = _completion(
        threshold_frozen=True,
        threshold_search="THRESHOLD_FROZEN",
        threshold_value="0.2500000000",
        training_readiness="CALIBRATION_COMPLETE_MEASUREMENT_PENDING",
    )
    assert not validator.is_valid(frozen)
    frozen.update(
        {
            "false_high": 1,
            "high_recall": "0.500000",
            "leave_one_out_result": "PASS",
            "precision": "0.800000",
            "predicted_yes_support": 8,
            "quarantine_predicted_yes": 0,
            "reject_predicted_yes": 0,
            "true_high": 7,
        }
    )
    assert validator.is_valid(frozen)


def test_unknown_join_row_rejects_a_residual():
    loaded, registry = _schemas()
    validator = _validator(loaded["residual-threshold-support-join.schema.json"], registry)
    assert not validator.is_valid(_join(row_resolution_status="UNKNOWN", residual_score="0.1000000000"))
    assert validator.is_valid(_join(row_resolution_status="UNKNOWN", residual_score=None))


def test_ready_join_row_requires_a_residual():
    loaded, registry = _schemas()
    validator = _validator(loaded["residual-threshold-support-join.schema.json"], registry)
    assert not validator.is_valid(_join(residual_score=None))
    assert validator.is_valid(_join())


def test_sha256_rejects_uppercase_and_short_digests():
    loaded, registry = _schemas()
    wrapper = {
        "$id": "https://hyperlex.local/schemas/residual-threshold-decision.schema.json",
        "$ref": "residual-threshold-common.schema.json#/$defs/sha256",
    }
    validator = _validator(wrapper, registry)
    assert validator.is_valid("a" * 64)
    assert not validator.is_valid("A" * 64)
    assert not validator.is_valid("ab")
    errors = sorted(validator.iter_errors("AB"), key=lambda item: list(item.path))
    rendered = [f"{'/'.join(str(part) for part in error.path)}: {error.validator}" for error in errors]
    assert rendered
    assert all("AB" not in line for line in rendered)


def test_validator_writes_only_the_public_conformance_report():
    source = inspect.getsource(schema_mod)
    assert source.count(".write_text") == 1
    assert "open(" not in source
    assert "hlx-private" not in str(schema_mod.REPORT_PATH)
    assert schema_mod.REPORT_PATH.name == "CONFORMANCE.json"


def test_conformance_does_not_change_frozen_evidence():
    if not SOURCE.is_dir():
        pytest.skip("private reserve is absent")
    before = evidence_hashes(SOURCE)
    report = conformance_report()
    after = evidence_hashes(SOURCE)
    assert before == after
    assert report["calibration_evidence_modified"] is False
    assert report["changed_artifacts"] == []
    assert report["outcome"] == PASS
    assert report["schema_conformance_gaps"] == []
    assert report["semantic_conformance_gaps"] == []
    assert report["scientific_remediation"] is False
    assert report["training_authorized"] is False
    statuses = {row["status"] for row in report["results"]} | {row["status"] for row in report["semantic"]}
    assert statuses == {PASS}
    assert GAP not in statuses
    assert len(report["results"]) == 26
    assert len(report["semantic"]) == 18
