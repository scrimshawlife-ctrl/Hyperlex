"""Contract schemas and semantic checks do not rewrite frozen threshold artifacts."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from hyperlexical import residual_threshold_contract as contract
from hyperlexical.residual_threshold_contract import (
    EXPECTED_EVENTS,
    EXPECTED_LEDGER,
    EXPECTED_MEASUREMENT,
    EXPECTED_TRACKER,
    SOURCE,
    classify,
    evidence_hashes,
    load_schemas,
    schema_registry,
    semantic_checks,
    validate_directory,
)


def _validator(name: str):
    schemas = load_schemas()
    Draft202012Validator.check_schema(schemas[name])
    return Draft202012Validator(schemas[name], registry=schema_registry(schemas))


def test_contract_family_names_match_the_specification():
    assert set(load_schemas()) == {
        "calibration-failure.schema.json",
        "common.schema.json",
        "completion-receipt.schema.json",
        "confound-analysis.schema.json",
        "confound-decision.schema.json",
        "direction-analysis.schema.json",
        "direction-decision.schema.json",
        "operator-label-row.schema.json",
        "operator-labeling-receipt.schema.json",
        "resolution-receipt.schema.json",
        "resolution-row.schema.json",
        "score-receipt.schema.json",
        "score-row.schema.json",
        "support-join-row.schema.json",
        "support-reassessment.schema.json",
        "surface-draw-receipt.schema.json",
        "surface-manifest-row.schema.json",
        "threshold-decision.schema.json",
        "threshold-search.schema.json",
    }


def test_valid_unfrozen_decision_passes_and_missing_field_fails():
    validator = _validator("calibration-failure.schema.json")
    document = {
        "failed_gate": "precision_gate",
        "failure_state": "NO_THRESHOLD_PASSES_PRECISION_GATE",
        "schema": "hyperlex.residual_threshold_v2_calibration_completion_failure.v1",
        "threshold_frozen": False,
        "threshold_value": None,
    }
    assert validator.is_valid(document)
    del document["failed_gate"]
    assert not validator.is_valid(document)


def test_bad_sha256_and_invalid_enum_fail():
    validator = _validator("support-join-row.schema.json")
    row = {
        "calibration_row_id": 1,
        "operator_label": "HIGH",
        "pos": "noun",
        "pwn30_synset": "noun:01234567",
        "residual_score": None,
        "row_id": "a" * 64,
        "row_resolution_status": "UNKNOWN",
        "surface": "example phrase",
    }
    assert validator.is_valid(row)
    assert not validator.is_valid({**row, "row_id": "A" * 64})
    assert not validator.is_valid({**row, "row_id": "ab"})
    assert not validator.is_valid({**row, "operator_label": "MAYBE"})


def test_unfrozen_threshold_rejects_a_numeric_value():
    validator = _validator("threshold-decision.schema.json")
    assert not validator.is_valid(
        {
            "schema": "hyperlex.residual_threshold_v2_threshold_frozen.v1",
            "threshold_frozen": False,
            "threshold_value": "0.2500000000",
        }
    )


def test_frozen_threshold_rejects_null_and_accepts_metrics():
    validator = _validator("threshold-decision.schema.json")
    frozen = {
        "false_high": 1,
        "high_recall": "0.500000",
        "leave_one_out_result": "PASS",
        "precision": "0.800000",
        "predicted_yes_support": 8,
        "quarantine_predicted_yes": 0,
        "reject_predicted_yes": 0,
        "schema": "hyperlex.residual_threshold_v2_threshold_frozen.v1",
        "threshold_frozen": True,
        "threshold_value": None,
        "true_high": 7,
        "wilson_lower": "0.500000",
        "wilson_upper": "0.900000",
    }
    assert not validator.is_valid(frozen)
    frozen["threshold_value"] = "0.2500000000"
    assert validator.is_valid(frozen)


def test_completion_receipt_is_not_classified_as_a_generic_receipt():
    assert classify("RESIDUAL_THRESHOLD_V2_CALIBRATION_COMPLETION_RECEIPT.json") == "completion-receipt.schema.json"
    assert classify("RESIDUAL_THRESHOLD_V2_SURFACE_DRAW_RECEIPT.json") == "surface-draw-receipt.schema.json"
    assert classify("RESIDUAL_THRESHOLD_V2_THRESHOLD_FROZEN.json") == "threshold-decision.schema.json"


def _write(path: Path, payload) -> None:
    if isinstance(payload, list):
        path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in payload), encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _surface(row_id: str, synset: str, order: int) -> dict:
    return {
        "allocation_rule_id": "positional_stratified_hash_round_robin_quota_v2",
        "frozen_gloss": "gloss",
        "global_draw_order": order,
        "normalized_text_sha256": row_id,
        "pos": "noun",
        "pwn30_synset": synset,
        "row_id": row_id,
        "source_identity": "wordnet-3.0",
        "stratum_id": "noun:2",
        "surface": "example phrase",
        "surface_role": "CALIBRATION_V2" if order <= 200 else "MEASUREMENT_V2",
        "token_count": 2,
        "within_stratum_order": 1,
    }


def test_semantic_validator_rejects_identity_synset_measurement_hash_and_total_mismatches(tmp_path: Path):
    row_ids = [f"{index:064x}" for index in range(200)]
    manifest = [_surface(row_ids[index], f"noun:{index:08d}", index + 1) for index in range(200)]
    labels = [
        {
            "calibration_row_id": index + 1,
            "operator_evidence": "STRONG_IDIOM",
            "operator_label": "HIGH",
            "operator_note": "lexicalized",
            "pos": "noun",
            "pwn30_synset": f"noun:{index:08d}",
            "review_status": "REVIEWED",
            "row_id": row_ids[index],
            "schema": "hyperlex.residual_threshold_v2_operator_label.v1",
            "surface": "example phrase",
        }
        for index in range(200)
    ]
    join = [
        {
            "calibration_row_id": index + 1,
            "operator_label": "HIGH",
            "pos": "noun",
            "pwn30_synset": f"noun:{index:08d}",
            "residual_score": "0.1000000000" if index < 60 else None,
            "row_id": row_ids[index],
            "row_resolution_status": "RESIDUAL_READY" if index < 60 else "UNKNOWN",
            "surface": "example phrase",
        }
        for index in range(200)
    ]
    measurement = [_surface(f"{index + 400:064x}", f"verb:{index:08d}", 201 + index) for index in range(200)]
    _write(tmp_path / "RESIDUAL_THRESHOLD_V2_CALIBRATION_MANIFEST.jsonl", manifest)
    _write(tmp_path / "RESIDUAL_THRESHOLD_V2_OPERATOR_LABELS.jsonl", labels)
    _write(tmp_path / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SUPPORT_JOIN.jsonl", join)
    _write(tmp_path / "RESIDUAL_THRESHOLD_V2_MEASUREMENT_MANIFEST.jsonl", measurement)
    measurement_hash = __import__("hashlib").sha256((tmp_path / "RESIDUAL_THRESHOLD_V2_MEASUREMENT_MANIFEST.jsonl").read_bytes()).hexdigest()
    baseline = semantic_checks(tmp_path, measurement_hash)
    assert all(row["status"] == "PASS" for row in baseline)

    drifted = [dict(row) for row in labels]
    drifted[0]["row_id"] = "b" * 64
    _write(tmp_path / "RESIDUAL_THRESHOLD_V2_OPERATOR_LABELS.jsonl", drifted)
    assert any(row["check"] == "row_set_equality" and row["status"] != "PASS" for row in semantic_checks(tmp_path, measurement_hash))

    _write(tmp_path / "RESIDUAL_THRESHOLD_V2_OPERATOR_LABELS.jsonl", labels)
    duplicated = [dict(row) for row in manifest]
    duplicated[1]["pwn30_synset"] = duplicated[0]["pwn30_synset"]
    _write(tmp_path / "RESIDUAL_THRESHOLD_V2_CALIBRATION_MANIFEST.jsonl", duplicated)
    assert any(row["check"] == "calibration_synset_unique" and row["status"] != "PASS" for row in semantic_checks(tmp_path, measurement_hash))

    _write(tmp_path / "RESIDUAL_THRESHOLD_V2_CALIBRATION_MANIFEST.jsonl", manifest)
    assert any(row["check"] == "measurement_manifest_unchanged" and row["status"] != "PASS" for row in semantic_checks(tmp_path, "a" * 64))

    short = join[:-1]
    _write(tmp_path / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SUPPORT_JOIN.jsonl", short)
    assert any(row["check"] == "ready_plus_unknown" and row["status"] != "PASS" for row in semantic_checks(tmp_path, measurement_hash))


def test_validator_writes_only_the_public_contract_report():
    source = inspect.getsource(contract)
    assert source.count(".write_text") == 1
    assert "open(" not in source
    assert "hlx-private" not in str(contract.REPORT_PATH)


def test_historical_validation_does_not_mutate_evidence():
    if not SOURCE.is_dir():
        pytest.skip("private reserve is absent")
    before = evidence_hashes(SOURCE)
    report = validate_directory(SOURCE)
    after = evidence_hashes(SOURCE)
    assert before == after
    assert report["calibration_evidence_modified"] is False
    assert report["historical_artifact_mutated"] is False
    assert report["training_authorized"] is False
    assert report["threshold_decision_emitted"] is False
    assert report["outcome"] == "HISTORICAL_VALIDATION_COMPLETE"
    assert report["schema_conformance_gaps"] == []
    assert report["semantic_conformance_gaps"] == []
    ledger = SOURCE.parents[1]
    assert __import__("hashlib").sha256((ledger / "events.jsonl").read_bytes()).hexdigest() == EXPECTED_EVENTS
    assert __import__("hashlib").sha256((ledger / "ledger.json").read_bytes()).hexdigest() == EXPECTED_LEDGER
    tracker = ledger / "operator-review/HLX-EVAL-UNBIND-SENSE-SCREEN-V1-HYPOTHESIS-001/HYPOTHESIS.json"
    assert __import__("hashlib").sha256(tracker.read_bytes()).hexdigest() == EXPECTED_TRACKER
    assert __import__("hashlib").sha256((SOURCE / "RESIDUAL_THRESHOLD_V2_MEASUREMENT_MANIFEST.jsonl").read_bytes()).hexdigest() == EXPECTED_MEASUREMENT
