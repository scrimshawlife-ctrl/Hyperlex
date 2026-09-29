"""The compact lifecycle keeps the scientific gates and drops the extra states."""

import copy

import pytest

from hyperlexical.experiment_lifecycle import (
    AUTHORIZE_PROMOTION,
    READY,
    RUNNING,
    SETTLED_FAIL,
    SETTLED_INVALID,
    SETTLED_PASS,
    LifecycleError,
    begin_run,
    draft,
    map_historical,
    preflight,
    preregister,
    promote,
    select_006_historical_markers,
    select_006_readiness,
    settle,
)

STAMP = "2026-09-29T00:00:00Z"
DIGEST = "ab" * 32


def _definition(experiment_id: str = "HLX-EXP-TEST") -> dict:
    return {
        "acceptance_rules": {"epsilon": 0, "compensation": False},
        "candidate_schedule": {"max_epochs": 12},
        "control_schedule": {"max_epochs": 40},
        "evaluation_design": {"reserve": "frozen"},
        "experiment_id": experiment_id,
        "hypothesis": "The candidate schedule preserves the primary metric.",
        "promotion_policy": {"pass_promotes_best": False, "separate_from_settlement": True},
        "selection_metric": "classify_macro_f1_nonnone",
        "shared_hyperparameters": {"learning_rate": "2e-5"},
        "training_data_sha256": DIGEST,
        "warm_start_sha256": DIGEST,
    }


def _obs(ok: bool = True, reason: str | None = None, decision: str | None = None) -> dict:
    body = {"artifact": "artifact", "ok": ok, "sha256": DIGEST, "timestamp": STAMP}
    if decision is not None:
        body["decision"] = decision
    if not ok:
        body["blocking_reason"] = reason
    return body


def _all_pass() -> dict:
    observations = {key: _obs() for key in (
        "environment",
        "isolation",
        "ledger",
        "loader",
        "metric_computability",
        "preregistration",
        "provenance",
        "reserve",
        "schedule",
        "telemetry_plan",
        "thresholds",
        "training_data",
        "warm_start",
    )}
    observations["operator_authorization"] = _obs(decision="AUTHORIZE")
    return observations


def _ready():
    registered = preregister("HLX-EXP-TEST", _definition())
    return preflight(registered, _all_pass())


def test_valid_experiment_reaches_ready_in_one_preflight():
    record = _ready()
    assert record["state"] == READY
    assert record["next_action"] == "RUN"
    assert record["blocking_reasons"] == []
    assert all(item["status"] == "PASS" for item in record["evidence"].values())


@pytest.mark.parametrize(
    ("check", "reason"),
    [
        ("preregistration", "PREREGISTRATION_MISMATCH"),
        ("warm_start", "DATA_INTEGRITY_FAILURE"),
        ("training_data", "DATA_INTEGRITY_FAILURE"),
        ("reserve", "RESERVE_INVALID"),
        ("isolation", "EVALUATION_LEAKAGE"),
        ("metric_computability", "METRIC_NONCOMPUTABLE"),
        ("loader", "LOADER_INVALID"),
        ("environment", "ENVIRONMENT_MISMATCH"),
        ("telemetry_plan", "TELEMETRY_PLAN_INVALID"),
        ("operator_authorization", "OPERATOR_AUTHORIZATION_MISSING"),
    ],
)
def test_each_failed_check_blocks_ready(check: str, reason: str):
    observations = _all_pass()
    if check == "operator_authorization":
        observations[check] = _obs(ok=False, reason=reason, decision="TRAINING_READY")
    else:
        observations[check] = _obs(ok=False, reason=reason)
    record = preflight(preregister("HLX-EXP-TEST", _definition()), observations)
    assert record["state"] == "PREREGISTERED"
    assert {"check": check, "blocking_reason": reason} in record["blocking_reasons"]


def test_training_ready_is_not_operator_authorization():
    observations = _all_pass()
    observations["operator_authorization"] = {
        "artifact": "admission",
        "decision": "TRAINING_READY",
        "inferred_from": "TRAINING_READY",
        "ok": True,
        "sha256": DIGEST,
        "timestamp": STAMP,
    }
    record = preflight(preregister("HLX-EXP-TEST", _definition()), observations)
    assert record["state"] == "PREREGISTERED"
    assert record["evidence"]["operator_authorization"]["blocking_reason"] == "OPERATOR_AUTHORIZATION_MISSING"


def test_ready_cannot_run_without_operator_authorization():
    record = _ready()
    stripped = copy.deepcopy(record)
    stripped["evidence"]["operator_authorization"] = {
        "artifact": "authorization",
        "blocking_reason": "OPERATOR_AUTHORIZATION_MISSING",
        "sha256": None,
        "status": "FAIL",
        "timestamp": STAMP,
    }
    with pytest.raises(LifecycleError, match="OPERATOR_AUTHORIZATION_MISSING"):
        begin_run(stripped)


def test_first_optimizer_step_enters_running():
    running = begin_run(_ready())
    assert running["state"] == RUNNING
    assert running["running_since_optimizer_step"] == 1
    assert running["promotion_applied"] is False


def test_valid_threshold_failure_settles_fail():
    settled = settle(begin_run(_ready()), scientifically_valid=True, acceptance_passed=False)
    assert settled["state"] == SETTLED_FAIL
    assert settled["promotion_applied"] is False


def test_integrity_failure_settles_invalid_rather_than_fail():
    settled = settle(begin_run(_ready()), scientifically_valid=False, acceptance_passed=True)
    assert settled["state"] == SETTLED_INVALID
    assert settled["state"] != SETTLED_FAIL


def test_settled_pass_does_not_promote_until_a_separate_decision():
    passed = settle(begin_run(_ready()), scientifically_valid=True, acceptance_passed=True)
    assert passed["state"] == SETTLED_PASS
    assert passed["promotion_applied"] is False
    with pytest.raises(LifecycleError):
        promote(passed, "AUTHORIZE")
    promoted = promote(passed, AUTHORIZE_PROMOTION)
    assert promoted["state"] == "PROMOTED"
    assert promoted["promotion_applied"] is True
    failed = settle(begin_run(_ready()), scientifically_valid=True, acceptance_passed=False)
    invalid = settle(begin_run(_ready()), scientifically_valid=False, acceptance_passed=False)
    with pytest.raises(LifecycleError):
        promote(failed, AUTHORIZE_PROMOTION)
    with pytest.raises(LifecycleError):
        promote(invalid, AUTHORIZE_PROMOTION)


def test_historical_markers_map_deterministically_and_select_006_is_ready():
    first = map_historical(select_006_historical_markers(timestamp=STAMP))
    second = map_historical(select_006_historical_markers(timestamp=STAMP))
    assert first == second
    assert first["state"] == READY
    assert first["next_action"] == "RUN"
    assert first["experiment_id"] == "HLX-EXP-2026-09-29-SELECT-006"
    assert first["evidence"]["loader"]["status"] == "PASS"
    assert first["evidence"]["reserve"]["status"] == "PASS"
    assert first["evidence"]["operator_authorization"]["status"] == "PASS"
    ready = select_006_readiness(timestamp=STAMP)
    assert ready == first
    withheld = select_006_historical_markers(timestamp=STAMP)
    withheld["training_launch_authorized"] = False
    withheld["operator_decision"] = None
    withheld["state"] = "TRAINING_READY"
    blocked = map_historical(withheld)
    assert blocked["state"] == "PREREGISTERED"
    assert blocked["evidence"]["operator_authorization"]["blocking_reason"] == "OPERATOR_AUTHORIZATION_MISSING"


def test_draft_does_not_authorize_compute_and_science_is_frozen_after_preregistration():
    opened = draft("HLX-EXP-TEST")
    assert opened["state"] == "DRAFT"
    assert opened["promotion_applied"] is False
    registered = preregister("HLX-EXP-TEST", _definition())
    changed = _definition()
    changed["hypothesis"] = "A different hypothesis."
    from hyperlexical.experiment_lifecycle import assert_same_science

    with pytest.raises(LifecycleError, match="PREREGISTRATION_MISMATCH"):
        assert_same_science(registered, changed)
