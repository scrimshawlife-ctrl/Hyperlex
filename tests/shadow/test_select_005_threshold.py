"""SELECT-005 thresholds seal strict improvement and zero degradation."""

import hashlib
from pathlib import Path

from hyperlexical.select_005_completion import threshold_authorization_proposal
from hyperlexical.select_005_reserve import canonical_json, sha256_text
from hyperlexical.select_005_threshold import (
    SCHEMA_SHA256,
    apply_decision,
    authorization_sha256,
    schema_validation_report,
    sealed_authorization,
    semantic_errors,
    semantic_validation_report,
)

REPO = Path(__file__).resolve().parents[2]
HARVEST_SHA256 = "8f58f30ca85af2e476064c7afea9498b02a53d71c4890d38b4cdc2baaf83021c"
COMPLETION_SHA256 = "f9728185f171b8d5c3eeea326e30e230e05def80885c43cbf79c13c64f4095ba"


def _scores(primary: float, accuracy: float, observed: float, unbind: float) -> dict:
    return {
        "classification_accuracy": accuracy,
        "classify_macro_f1_nonnone": primary,
        "observed_label_accuracy": observed,
        "unbind_clean_exact": unbind,
    }


def test_sealed_artifact_has_no_nulls_and_validates():
    payload = sealed_authorization()
    assert payload["sealed"] is True
    assert payload["experiment_id"] == "HLX-EXP-2026-09-27-SELECT-005"
    assert payload["training_launch_authorized"] is False
    assert payload["inherited_from_select_004"] is False
    assert payload["comparison_baseline"] == "SELECT-005 control arm"
    for name, value in payload["decision_thresholds"].items():
        assert value is not None
        assert value == 0
    for item in payload["metrics"]:
        assert item["numeric_threshold"] is not None
    assert schema_validation_report()["result"] == "PASS"
    assert semantic_validation_report()["result"] == "PASS"
    assert semantic_errors(payload) == []
    assert authorization_sha256() == sha256_text(canonical_json(payload))


def test_primary_equality_fails_and_a_positive_delta_passes_that_gate():
    control = _scores(0.20, 0.50, 0.40, 0.10)
    tie = apply_decision(control, _scores(0.20, 0.50, 0.40, 0.10))
    assert tie["pass"] is False
    assert tie["outcome"] == "FAIL"
    primary = next(gate for gate in tie["gates"] if gate["metric"] == "classify_macro_f1_nonnone")
    assert primary["reason"] == "PRIMARY_NOT_STRICT"
    improved = apply_decision(control, _scores(0.21, 0.50, 0.40, 0.10))
    assert improved["pass"] is True
    assert improved["outcome"] == "PASS"


def test_each_preservation_metric_vetoes_alone():
    control = _scores(0.20, 0.50, 0.40, 0.10)
    drops = {
        "classification_accuracy": _scores(0.21, 0.49, 0.40, 0.10),
        "observed_label_accuracy": _scores(0.21, 0.50, 0.39, 0.10),
        "unbind_clean_exact": _scores(0.21, 0.50, 0.40, 0.09),
    }
    for name, candidate in drops.items():
        result = apply_decision(control, candidate)
        assert result["pass"] is False
        failed = [gate["metric"] for gate in result["gates"] if not gate["pass"]]
        assert failed == [name]


def test_missing_and_noncomputable_metrics_fail():
    control = _scores(0.20, 0.50, 0.40, 0.10)
    candidate = _scores(0.21, 0.50, 0.40, 0.10)
    del candidate["observed_label_accuracy"]
    missing = apply_decision(control, candidate)
    assert missing["pass"] is False
    observed = next(gate for gate in missing["gates"] if gate["metric"] == "observed_label_accuracy")
    assert observed["reason"] == "MISSING"
    bad = _scores(0.21, 0.50, 0.40, 0.10)
    bad["unbind_clean_exact"] = float("nan")
    nan_result = apply_decision(control, bad)
    assert nan_result["pass"] is False
    unbind = next(gate for gate in nan_result["gates"] if gate["metric"] == "unbind_clean_exact")
    assert unbind["reason"] == "NON_COMPUTABLE"


def test_wrong_experiment_and_unsealed_proposal_do_not_authorize():
    payload = sealed_authorization()
    payload["experiment_id"] = "HLX-EXP-2026-09-26-SELECT-004"
    assert any("experiment_id" in item for item in semantic_errors(payload))
    proposal = threshold_authorization_proposal()
    assert proposal["sealed"] is False
    assert proposal["decision_thresholds"] == {}
    assert any(item["numeric_threshold"] is None for item in proposal["metrics"])
    assert semantic_validation_report(proposal)["result"] == "FAIL"


def test_select_004_floors_are_not_the_sealed_numbers():
    thresholds = sealed_authorization()["decision_thresholds"]
    assert thresholds["classification_accuracy"] != 0.02
    assert thresholds["observed_label_accuracy"] != 0.05
    assert thresholds["unbind_clean_exact"] != 0.01
    assert "classify_macro_f1_nonnone" in thresholds


def test_schema_harvest_and_proposal_module_stay_put():
    schema = (
        REPO
        / "specs/007-hyperlexical-model/schemas/hyperlex/select/threshold-authorization.schema.json"
    )
    harvest = REPO / "scripts/shadow/hyperlexical/select_005_harvest.py"
    completion = REPO / "scripts/shadow/hyperlexical/select_005_completion.py"
    assert hashlib.sha256(schema.read_bytes()).hexdigest() == SCHEMA_SHA256
    assert hashlib.sha256(harvest.read_bytes()).hexdigest() == HARVEST_SHA256
    assert hashlib.sha256(completion.read_bytes()).hexdigest() == COMPLETION_SHA256
