"""The launch-authorization spec defines an edge. It does not authorize or train."""

import json
from pathlib import Path

import pytest

from hyperlexical.select_005_training_launch_authorization import (
    ADMISSION_RECEIPT_SHA256,
    ENVIRONMENT_SHA256,
    LAUNCH_TRANSITION,
    PREREGISTRATION_SHA256,
    RESERVE_MANIFEST_SHA256,
    THRESHOLD_AUTHORIZATION_SHA256,
    WARM_START_SHA256,
    _validate,
    launch_authorization_spec,
    spec_receipt,
)
from hyperlexical.select_contract_schema import (
    training_launch_authorization_schema_errors,
    training_launch_authorization_spec_schema_errors,
)

REPO = Path(__file__).resolve().parents[2]


def _authorization_record() -> dict:
    spec = launch_authorization_spec()
    pins = spec["required_pins"]
    return {
        "admission_receipt_sha256": pins["admission_receipt_sha256"],
        "best_changed": False,
        "environment_sha256": pins["environment_sha256"],
        "epochs": 0,
        "executes_training": False,
        "experiment_id": pins["experiment_id"],
        "gradient_steps": 0,
        "next_legal_transition": LAUNCH_TRANSITION,
        "operator_decision": spec["authorization_record"]["operator_decision_required"],
        "optimizer_constructed": False,
        "preregistration_sha256": pins["preregistration_sha256"],
        "ready_to_train": True,
        "reserve_manifest_sha256": pins["reserve_manifest_sha256"],
        "schedule": spec["sealed_schedule"],
        "schema": spec["authorization_record"]["schema"],
        "scientific_variable": "train_schedule",
        "state": "TRAINING_LAUNCH_AUTHORIZED",
        "threshold_authorization_sha256": pins["threshold_authorization_sha256"],
        "training_launch_authorized": True,
        "training_started": False,
        "transition": "SELECT_005_TRAINING_LAUNCH_AUTHORIZATION",
        "warm_start_sha256": pins["warm_start_sha256"],
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


def test_receipt_is_deterministic_and_module_has_no_trainer():
    assert spec_receipt() == spec_receipt()
    assert len(spec_receipt()["record_sha256"]) == 64
    text = (REPO / "scripts/shadow/hyperlexical/select_005_training_launch_authorization.py").read_text()
    for banned in ("import torch", "AdamW", "urllib", "import requests", "httpx", "urlopen", "Popen"):
        assert banned not in text
    assert "does not authorize compute" in text
    assert "does not train" in text
