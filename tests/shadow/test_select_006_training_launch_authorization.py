"""SELECT-006 launch authorization records the operator decision and does not train."""

import json
from pathlib import Path

import pytest

from hyperlexical.select_006_efficiency_preservation import (
    EPSILON,
    _schedules,
    _shared_settings,
    vocabulary_expansion_pin,
)
from hyperlexical.select_006_training_launch_authorization import (
    ACTIVE_EVAL_RESERVE,
    ADMISSION_RECEIPT_SHA256,
    HISTORICAL_PIN_STATUS,
    LAUNCH_TRANSITION,
    LEDGER_EVENTS_SHA256,
    LEDGER_PROJECTION_SHA256,
    PREREGISTRATION_SHA256,
    SLICE_COUNTS,
    THRESHOLD_SHA256,
    VERIFIED,
    LaunchAuthorizationError,
    require_authorization_record,
    seal_training_launch_authorization,
    training_launch_authorization,
)
from hyperlexical.select_contract_schema import (
    select_006_training_launch_authorization_schema_errors,
    training_launch_authorization_schema_errors,
)

REPO = Path(__file__).resolve().parents[2]


def _evidence() -> dict:
    record = training_launch_authorization()
    zero_init = record["zero_init"]
    reserve = record["reserve"]
    return {
        "active_eval_reserve": reserve["active_select_006_eval_reserve"],
        "admission_overlay_environment_hash": record["environment"]["admission_overlay_environment_hash"],
        "admission_receipt_sha256": record["admission_receipt_sha256"],
        "admission_result": "ADMISSION_PASS",
        "baseline_env_sha256": record["environment"]["baseline_env_sha256"],
        "best_changed": False,
        "best_sha256": record["best_sha256"],
        "candidate_config_sha256": record["environment"]["candidate_config_sha256"],
        "candidate_env_sha256": record["environment"]["candidate_env_sha256"],
        "combined_witness_sha256": zero_init["combined_witness_sha256"],
        "configs_agree": True,
        "control_config_sha256": record["environment"]["control_config_sha256"],
        "decision_rule": record["decision_rule"],
        "epochs": 0,
        "epsilon": 0,
        "execution_loader_status": VERIFIED,
        "experiment_id": record["experiment_id"],
        "filler_bias_sha256": zero_init["filler_bias_sha256"],
        "filler_weight_sha256": zero_init["filler_weight_sha256"],
        "gradient_steps": 0,
        "historical_vocabulary_pin_rewritten": False,
        "historical_vocabulary_pin_sha256": zero_init["historical_vocabulary_pin_sha256"],
        "historical_vocabulary_pin_status": HISTORICAL_PIN_STATUS,
        "isolation": "PASS",
        "ledger": record["ledger"],
        "ledger_replay": "PASS",
        "metric_computability": "PASS",
        "optimizer_constructed": False,
        "output_absent": True,
        "pre_training_launch_authorized": False,
        "pre_training_started": False,
        "preregistration_sha256": PREREGISTRATION_SHA256,
        "provenance": "PASS",
        "ready_to_train": True,
        "reserve_manifest_sha256": record["reserve_manifest_sha256"],
        "reserve_state": "RESERVE_FROZEN",
        "role_bias_sha256": zero_init["role_bias_sha256"],
        "role_weight_sha256": zero_init["role_weight_sha256"],
        "routing_validation": "PASS",
        "schedule": record["schedule"],
        "shared_settings": record["shared_settings"],
        "slice_counts": dict(SLICE_COUNTS),
        "status": "TRAINING_READY",
        "threshold_authorization_sha256": THRESHOLD_SHA256,
        "warm_start_sha256": record["warm_start_sha256"],
        "weights_mutated_by_training": False,
        "witness_file_sha256": zero_init["witness_file_sha256"],
    }


def test_record_authorizes_launch_and_performs_zero_training():
    record = training_launch_authorization()
    assert record["operator_decision"] == "AUTHORIZE"
    assert record["state"] == "TRAINING_LAUNCH_AUTHORIZED"
    assert record["training_launch_authorized"] is True
    assert record["training_started"] is False
    assert record["executes_training"] is False
    assert record["ready_to_train"] is True
    assert record["optimizer_constructed"] is False
    assert record["epochs"] == 0
    assert record["gradient_steps"] == 0
    assert record["weights_mutated_by_training"] is False
    assert record["best_changed"] is False
    assert record["training_output_directory_created"] is False
    assert record["epsilon"] == 0
    assert EPSILON == 0
    assert record["next_legal_transition"] == LAUNCH_TRANSITION
    assert select_006_training_launch_authorization_schema_errors(record) == []


def test_ready_to_train_does_not_satisfy_the_select005_authorization_schema():
    record = training_launch_authorization()
    assert training_launch_authorization_schema_errors(record)


def test_historical_vocabulary_pin_stays_unimplemented():
    assert vocabulary_expansion_pin()["execution_loader_status"] == "NOT_YET_IMPLEMENTED"
    zero_init = training_launch_authorization()["zero_init"]
    assert zero_init["historical_vocabulary_pin_status"] == "NOT_YET_IMPLEMENTED"
    assert zero_init["historical_vocabulary_pin_rewritten"] is False
    assert zero_init["execution_loader_status"] == "ZERO_INIT_LOADER_VERIFIED"


def test_schedule_shared_settings_and_threshold_rule_are_the_sealed_ones():
    record = training_launch_authorization()
    control, candidate = _schedules()
    assert record["schedule"] == {"candidate": candidate, "control": control}
    assert record["shared_settings"] == _shared_settings()
    assert record["shared_settings"]["learning_rate"] == "2e-5"
    assert record["shared_settings"]["batch_size"] == 8
    assert record["shared_settings"]["gradient_accumulation"] == 1
    assert record["shared_settings"]["seed_policy"] == "HLX_SEED_UNSET_FROZEN"
    assert record["shared_settings"]["selection_metric"] == "classify_macro_f1_nonnone"
    assert record["shared_settings"]["max_len"] == 64
    assert record["shared_settings"]["filler_filter"] == "strict"
    assert record["shared_settings"]["unbind_curriculum"] is False
    assert record["shared_settings"]["unbind_every_n"] == 1
    assert record["shared_settings"]["unbind_loss_weight"] == 1.0
    assert record["shared_settings"]["unbind_primary"] == "mixed"
    rule = record["decision_rule"]
    assert rule["compensation"] is False
    assert rule["primary_equality"] == "PASS"
    assert rule["efficiency"] == "candidate_optimizer_steps * 4 <= control_optimizer_steps"
    assert rule["missing_required_metric"] == "FAIL"
    assert rule["noncomputable_required_metric"] == "FAIL"
    assert rule["primary_strict_increase_required"] is False
    assert record["reserve"]["active_select_006_eval_reserve"] == ACTIVE_EVAL_RESERVE
    assert record["reserve"]["slice_counts"] == SLICE_COUNTS
    assert record["reserve"]["identities_consumed"] == 0
    assert record["ledger"]["authorization_recorded_in_identity_ledger"] is False
    assert record["ledger"]["event_type"] is None
    assert record["ledger"]["events_sha256"] == LEDGER_EVENTS_SHA256
    assert record["ledger"]["projection_sha256"] == LEDGER_PROJECTION_SHA256
    assert record["admission_receipt_sha256"] == ADMISSION_RECEIPT_SHA256


def test_pin_reserve_and_loader_mismatches_fail_closed():
    evidence = _evidence()
    evidence["preregistration_sha256"] = "0" * 64
    with pytest.raises(LaunchAuthorizationError, match="LAUNCH_AUTHORIZATION_PIN_MISMATCH: preregistration_sha256"):
        seal_training_launch_authorization("/tmp/select006-should-not-seal.json", evidence)

    evidence = _evidence()
    evidence["active_eval_reserve"] = 36
    with pytest.raises(LaunchAuthorizationError, match="LAUNCH_AUTHORIZATION_RESERVE_FAILURE: active_eval_reserve"):
        seal_training_launch_authorization("/tmp/select006-should-not-seal.json", evidence)

    evidence = _evidence()
    evidence["execution_loader_status"] = "NOT_YET_IMPLEMENTED"
    with pytest.raises(LaunchAuthorizationError, match="LAUNCH_AUTHORIZATION_LOADER_FAILURE: execution_loader_status"):
        seal_training_launch_authorization("/tmp/select006-should-not-seal.json", evidence)

    evidence = _evidence()
    evidence["status"] = "TRAINING_STARTED"
    with pytest.raises(LaunchAuthorizationError, match="LAUNCH_AUTHORIZATION_PREFLIGHT_FAILURE: status"):
        seal_training_launch_authorization("/tmp/select006-should-not-seal.json", evidence)


def test_authorization_is_not_inferred_when_the_operator_decision_is_absent():
    record = training_launch_authorization()
    forged = dict(record)
    forged["operator_decision"] = "TRAINING_READY"
    with pytest.raises(LaunchAuthorizationError, match="LAUNCH_AUTHORIZATION_SCHEMA_FAILURE"):
        require_authorization_record(forged)


def test_seal_writes_once_and_refuses_to_overwrite(tmp_path: Path):
    target = tmp_path / "TRAINING_LAUNCH_AUTHORIZATION.json"
    sealed = seal_training_launch_authorization(str(target), _evidence())
    assert sealed["operator_decision"] == "AUTHORIZE"
    assert sealed["training_started"] is False
    assert json.loads(target.read_text(encoding="utf-8")) == sealed
    with pytest.raises(LaunchAuthorizationError, match="LAUNCH_AUTHORIZATION_SEAL_FAILURE"):
        seal_training_launch_authorization(str(target), _evidence())
    assert json.loads(target.read_text(encoding="utf-8"))["epochs"] == 0


def test_module_does_not_call_the_trainer():
    source = (
        REPO / "scripts/shadow/hyperlexical/select_006_training_launch_authorization.py"
    ).read_text(encoding="utf-8")
    assert "AdamW" not in source
    assert "run_loop" not in source
    assert "IdentityLedger" not in source
