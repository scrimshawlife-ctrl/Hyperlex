"""The launch-authorization spec defines an edge. It does not authorize or train."""

import json
from pathlib import Path

import pytest

from hyperlexical.select_005_training_launch_authorization import (
    ACTIVE_EVAL_RESERVE,
    ADMISSION_RECEIPT_SHA256,
    BEST_SHA256,
    ENVIRONMENT_SHA256,
    ISOLATION_SHA256,
    LAUNCH_TRANSITION,
    LEDGER_EVENTS_SHA256,
    LEDGER_PROJECTION_SHA256,
    PREREGISTRATION_SHA256,
    PROVENANCE_SHA256,
    REQUIRED_PINS,
    RESERVE_COUNTS,
    RESERVE_MANIFEST_SHA256,
    SPEC_RECEIPT_SHA256,
    THRESHOLD_AUTHORIZATION_SHA256,
    WARM_START_SHA256,
    _validate,
    launch_authorization_spec,
    require_authorization_record,
    seal_training_launch_authorization,
    spec_receipt,
    training_launch_authorization,
)
from hyperlexical.select_contract_schema import (
    training_launch_authorization_schema_errors,
    training_launch_authorization_spec_schema_errors,
)

REPO = Path(__file__).resolve().parents[2]


def _authorization_record() -> dict:
    return training_launch_authorization()


def _evidence() -> dict:
    return {
        "active_eval_reserve": ACTIVE_EVAL_RESERVE,
        "admission_result": "ADMISSION_PASS",
        "best_changed": False,
        "best_sha256": BEST_SHA256,
        "epochs": 0,
        "gradient_steps": 0,
        "isolation_sha256": ISOLATION_SHA256,
        "ledger_events_sha256": LEDGER_EVENTS_SHA256,
        "ledger_projection_sha256": LEDGER_PROJECTION_SHA256,
        "ledger_replay": "PASS",
        "optimizer_constructed": False,
        "output_absent": True,
        "pins": dict(REQUIRED_PINS),
        "provenance_sha256": PROVENANCE_SHA256,
        "ready_to_train": True,
        "reserve_counts": dict(RESERVE_COUNTS),
        "reserve_isolation": "PASS",
        "reserve_provenance": "PASS",
        "schedule": launch_authorization_spec()["sealed_schedule"],
        "spec_receipt_sha256": SPEC_RECEIPT_SHA256,
        "spec_state": "TRAINING_LAUNCH_AUTHORIZATION_SPEC_SEALED",
        "status": "TRAINING_READY",
        "training_launch_authorized": False,
        "training_started": False,
        "weights_mutated": False,
    }


def test_spec_separates_readiness_from_authorization_and_does_not_train():
    spec = launch_authorization_spec()
    assert spec["ready_to_train"] is True
    assert spec["training_launch_authorized"] is False
    assert spec["training_started"] is False
    assert spec["executes_training"] is False
    assert spec["epochs"] == 0
    assert spec["gradient_steps"] == 0
    assert spec["optimizer_constructed"] is False
    assert spec["weights_mutated"] is False
    assert spec["best_changed"] is False
    assert spec["launch_legal"] is False
    assert "operator_decision" not in spec
    assert spec["authorization_record"]["sealed_by_this_spec"] is False
    assert spec["authorization_record"]["performs_training"] is False
    assert spec["authorization_record"]["operator_decision_required"] == "AUTHORIZE"
    assert spec["next_legal_transition"] == "SELECT_005_TRAINING_LAUNCH_AUTHORIZATION"
    assert spec["authorization_record"]["next_legal_transition_after_seal"] == LAUNCH_TRANSITION
    assert spec["edge"] == [
        "TRAINING_READY",
        "SELECT_005_TRAINING_LAUNCH_AUTHORIZATION",
        "TRAINING_LAUNCH_AUTHORIZED",
        "SELECT_005_TRAINING_LAUNCH",
        "TRAINING_STARTED",
    ]


def test_required_pins_match_the_sealed_artifacts():
    spec = launch_authorization_spec()
    pins = spec["required_pins"]
    assert pins["experiment_id"] == "HLX-EXP-2026-09-27-SELECT-005"
    assert pins["admission_receipt_sha256"] == ADMISSION_RECEIPT_SHA256
    assert pins["preregistration_sha256"] == PREREGISTRATION_SHA256
    assert pins["threshold_authorization_sha256"] == THRESHOLD_AUTHORIZATION_SHA256
    assert pins["reserve_manifest_sha256"] == RESERVE_MANIFEST_SHA256
    assert pins["environment_sha256"] == ENVIRONMENT_SHA256
    assert pins["warm_start_sha256"] == WARM_START_SHA256
    schedule = spec["sealed_schedule"]
    assert schedule["baseline"]["HYPERLEX_TRAIN_EPOCHS"] == "40"
    assert schedule["baseline"]["HYPERLEX_EARLY_STOP"] == "0"
    assert schedule["baseline"]["HYPERLEX_EARLY_STOP_MIN_EPOCHS"] is None
    assert schedule["baseline"]["HYPERLEX_EARLY_STOP_PATIENCE"] is None
    assert schedule["candidate"]["HYPERLEX_TRAIN_EPOCHS"] == "12"
    assert schedule["candidate"]["HYPERLEX_EARLY_STOP"] == "1"
    assert schedule["candidate"]["HYPERLEX_EARLY_STOP_MIN_EPOCHS"] == "4"
    assert schedule["candidate"]["HYPERLEX_EARLY_STOP_PATIENCE"] == "4"
    assert schedule["checkpoint_rule"] == {
        "restore_best": True,
        "strict_increase": True,
        "ties": "keep_earlier",
    }
    assert schedule["selection_metric"] == "classify_macro_f1_nonnone"


def test_schedule_definitions_match():
    schema_dir = REPO / "specs/007-hyperlexical-model/schemas/hyperlex/select"
    authorization = json.loads((schema_dir / "training-launch-authorization.schema.json").read_text())
    spec = json.loads((schema_dir / "training-launch-authorization-spec.schema.json").read_text())
    assert authorization["$defs"]["sealed_schedule"] == spec["$defs"]["sealed_schedule"]


def test_spec_validates_and_is_not_an_authorization_record():
    spec = launch_authorization_spec()
    assert training_launch_authorization_spec_schema_errors(spec) == []
    assert training_launch_authorization_schema_errors(spec)


def test_future_authorization_record_pins_zero_training():
    record = _authorization_record()
    assert training_launch_authorization_schema_errors(record) == []
    assert record["training_started"] is False
    assert record["epochs"] == 0
    assert record["gradient_steps"] == 0
    assert record["optimizer_constructed"] is False
    started = _authorization_record()
    started["training_started"] = True
    assert training_launch_authorization_schema_errors(started)
    stepped = _authorization_record()
    stepped["gradient_steps"] = 1
    assert training_launch_authorization_schema_errors(stepped)
    refused = _authorization_record()
    refused["operator_decision"] = "REFUSE"
    assert training_launch_authorization_schema_errors(refused)
    unarmed = _authorization_record()
    unarmed["training_launch_authorized"] = False
    assert training_launch_authorization_schema_errors(unarmed)


def test_refuses_to_treat_readiness_as_authorization():
    spec = launch_authorization_spec()
    spec["training_launch_authorized"] = True
    with pytest.raises(SystemExit, match="launch authorization"):
        _validate(spec)


def test_refuses_to_record_operator_authorization_on_the_spec():
    spec = launch_authorization_spec()
    spec["operator_decision"] = "AUTHORIZE"
    with pytest.raises(SystemExit, match="AUTHORIZE"):
        _validate(spec)


def test_authorization_seals_operator_decision_without_training(tmp_path):
    target = tmp_path / "launch-authorization-001" / "TRAINING_LAUNCH_AUTHORIZATION.json"
    record = seal_training_launch_authorization(str(target), _evidence())
    assert record["operator_decision"] == "AUTHORIZE"
    assert record["state"] == "TRAINING_LAUNCH_AUTHORIZED"
    assert record["training_launch_authorized"] is True
    assert record["training_started"] is False
    assert record["executes_training"] is False
    assert record["optimizer_constructed"] is False
    assert record["epochs"] == 0
    assert record["gradient_steps"] == 0
    assert record["next_legal_transition"] == LAUNCH_TRANSITION
    assert json.loads(target.read_text()) == record
    assert launch_authorization_spec()["training_launch_authorized"] is False
    with pytest.raises(SystemExit, match="LAUNCH_AUTHORIZATION_SEAL_FAILURE"):
        seal_training_launch_authorization(str(target), _evidence())


def test_pin_or_precondition_failure_does_not_seal(tmp_path):
    target = tmp_path / "TRAINING_LAUNCH_AUTHORIZATION.json"
    mismatched = _evidence()
    mismatched["pins"]["warm_start_sha256"] = "0" * 64
    with pytest.raises(SystemExit, match="LAUNCH_AUTHORIZATION_PIN_MISMATCH"):
        seal_training_launch_authorization(str(target), mismatched)
    assert not target.exists()
    schedule = _evidence()
    schedule["schedule"]["candidate"]["HYPERLEX_TRAIN_EPOCHS"] = "40"
    with pytest.raises(SystemExit, match="LAUNCH_AUTHORIZATION_PIN_MISMATCH"):
        seal_training_launch_authorization(str(target), schedule)
    assert not target.exists()
    replay = _evidence()
    replay["ledger_replay"] = "FAIL"
    with pytest.raises(SystemExit, match="LAUNCH_AUTHORIZATION_PRECONDITION_FAILURE"):
        seal_training_launch_authorization(str(target), replay)
    assert not target.exists()
    short = _evidence()
    short["active_eval_reserve"] = 77
    with pytest.raises(SystemExit, match="LAUNCH_AUTHORIZATION_PRECONDITION_FAILURE"):
        seal_training_launch_authorization(str(target), short)
    assert not target.exists()


def test_schema_failure_rejects_a_training_record():
    record = training_launch_authorization()
    record["gradient_steps"] = 1
    with pytest.raises(SystemExit, match="LAUNCH_AUTHORIZATION_SCHEMA_FAILURE"):
        require_authorization_record(record)


def test_receipt_is_deterministic_and_module_has_no_trainer():
    assert spec_receipt() == spec_receipt()
    assert len(spec_receipt()["record_sha256"]) == 64
    text = (REPO / "scripts/shadow/hyperlexical/select_005_training_launch_authorization.py").read_text()
    for banned in ("import torch", "AdamW", "urllib", "import requests", "httpx", "urlopen", "Popen"):
        assert banned not in text
    assert "does not authorize compute" in text
    assert "does not train" in text
