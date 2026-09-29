"""SELECT-005 metric thresholds, sealed before any candidate result exists.

The comparison is the candidate arm minus the control arm. The primary rule
matches ``note_strict_improvement``: a tie does not pass. Preservation allows
no degradation. SELECT-004's 0.02 / 0.05 / 0.01 floors are a different
experiment and are not copied. This module does not train, harvest, or score.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

from .select_005_completion import (
    BEST_NAME,
    BEST_SHA256,
    THRESHOLD_SCHEMA,
    WARM_START_NAME,
    WARM_START_SHA256,
)
from .select_005_reserve import EXPERIMENT_ID, canonical_json, sha256_text
from .select_contract_schema import threshold_schema_errors

TRANSITION = "SELECT_005_THRESHOLD_AUTHORIZATION"
AUTHORIZATION_STATE = "SEALED"
PREREGISTRATION_SHA256 = "c2dcf3b703f50cb8eb80bb6c2c45335071ded3c4ce89cc669e8a869eb3498baf"
SCHEMA_SHA256 = "35a1b70cc805cf4271831a2414fd9ac85dcc15e5d23ec951d2d37665e89109a1"
PARENT_COMMIT = "7b857e33c63f595b05f078749257bf1d586a8ca6"
COMPARISON_BASELINE = "SELECT-005 control arm"
COMPARISON_CANDIDATE = "SELECT-005 candidate arm"
PRIMARY_METRIC = "classify_macro_f1_nonnone"
PRESERVATION_METRICS = (
    "classification_accuracy",
    "observed_label_accuracy",
    "unbind_clean_exact",
)
REQUIRED_METRICS = (PRIMARY_METRIC, *PRESERVATION_METRICS)
SELECT_004_FLOORS = {
    "classification_accuracy": 0.02,
    "observed_label_accuracy": 0.05,
    "unbind_clean_exact": 0.01,
}


def _metric(name: str) -> dict[str, Any]:
    primary = name == PRIMARY_METRIC
    if primary:
        operator = "GT"
        direction = "strict_improvement"
        rule_kind = "relative_to_control"
        why = (
            "The sealed schedule says the candidate must strictly improve "
            "classify_macro_f1_nonnone over the control arm. "
            "note_strict_improvement keeps a checkpoint only when "
            "score > best_value, and a tie keeps the earlier epoch. "
            "The numeric threshold is 0 on candidate_minus_control with "
            "operator GT, so equality fails. No larger margin is declared."
        )
    else:
        operator = "GE"
        direction = "maximum_allowed_degradation"
        rule_kind = "maximum_allowed_degradation"
        why = (
            "This metric is a guardrail, not the optimized target. Both arms "
            "share initialization, export, scorer, optimizer constants, and "
            "seed policy, and the scorer is a ratio of integer counts. "
            "Equal counts therefore compare equal. The smallest justified "
            "tolerance is no degradation: candidate_minus_control >= 0. "
            "SELECT-005 has no sealed reserve size, so a 1/N band cannot be "
            "computed. A positive allowance would be a larger margin."
        )
    return {
        "comparison_basis": "candidate_minus_control",
        "derivation": why,
        "direction": direction,
        "equality": "FAIL" if primary else "PASS",
        "evidence_refs": [
            "specs/007-hyperlexical-model/evaluation-reserve.md SELECT-005 preregistration",
            "scripts/shadow/hyperlexical/loop.py note_strict_improvement",
            "scripts/shadow/hyperlexical/classify_metrics.py accuracy and macro_f1_nonnone",
            "SELECT-004 decision receipt ee493b7d73b5e00ae27ec681bb52405bbcf2983a16a0297edad225aec52b7225",
        ],
        "historical_evidence": (
            "SELECT-004 compared a different variable against seed-morph78 "
            "and allowed drops of 0.02, 0.05, and 0.01 on reserve sizes "
            "241, 123, and 250. Its one finished reserve run moved unbind "
            "clean exact by 0.008. Those sizes and that baseline are not "
            "SELECT-005's."
        ),
        "metric": name,
        "not_inherited_because": (
            "SELECT-004 floors were sized to that experiment's sealed "
            "reserve and to seed-morph78. SELECT-005's baseline is its own "
            "control arm, and its reserve is not frozen."
        ),
        "numeric_threshold": 0,
        "operator": operator,
        "rule_kind": rule_kind,
        "units": "score_delta",
    }


def sealed_authorization() -> dict[str, Any]:
    """The operator policy for SELECT-005. Every required number is 0 with an operator."""
    metrics = [_metric(name) for name in REQUIRED_METRICS]
    return {
        "authorization_state": AUTHORIZATION_STATE,
        "baseline": {
            "comparison_candidate": COMPARISON_CANDIDATE,
            "not_seed_morph78": True,
            "same_export_sha256": "64b7d3dede25047cb6dd2e5b663f7fa72946ec82ac1a8816ae34622d1aaac430",
            "same_initialization": WARM_START_NAME,
            "warm_start_sha256": WARM_START_SHA256,
        },
        "comparison_baseline": COMPARISON_BASELINE,
        "decision_rule": {
            "combined": (
                "PASS iff primary delta > 0 AND classification_accuracy "
                "delta >= 0 AND observed_label_accuracy delta >= 0 AND "
                "unbind_clean_exact delta >= 0"
            ),
            "compensation": False,
            "frozen_before_training": True,
            "missing_required_metric": "FAIL",
            "non_computable_required_metric": "FAIL",
            "preservation_equality_at_floor": "PASS",
            "primary_equality": "FAIL",
            "reserve_slice_floor_is_not_this_rule": (
                "unbind_clean >= 1 is reserve admission. "
                "unbind_clean_exact is the model-quality guardrail."
            ),
        },
        "decision_thresholds": {name: 0 for name in REQUIRED_METRICS},
        "derivation": (
            "Primary threshold 0 uses operator GT because the preregistered "
            "schedule and note_strict_improvement already require a strict "
            "increase. Preservation thresholds are 0 with operator GE because "
            "the paired arms share one scorer and no SELECT-005 sample size "
            "exists from which to justify a positive degradation band."
        ),
        "direction": "candidate_minus_control",
        "experiment_id": EXPERIMENT_ID,
        "inherited_from_select_004": False,
        "metrics": metrics,
        "not_seed_morph78": True,
        "operator": {
            "decision": "AUTHORIZE_SELECT_005_THRESHOLDS",
            "not_a_transfer": (
                "SELECT-004 decision_thresholds 0.02, 0.05, and 0.01 stay on "
                "HLX-EXP-2026-09-26-SELECT-004."
            ),
            "recorded_by": "Hyperlex Cloud Agent",
            "scope": EXPERIMENT_ID,
            "training_launch_authorized": False,
        },
        "preregistration_edited": False,
        "preregistration_sha256": PREREGISTRATION_SHA256,
        "primary_comparison_supported_by_schedule_design": (
            "candidate classify_macro_f1_nonnone > control "
            "classify_macro_f1_nonnone"
        ),
        "primary_metric": {
            "comparison_basis": "candidate_minus_control",
            "equality": "FAIL",
            "name": PRIMARY_METRIC,
            "operator": "GT",
            "strict_improvement": True,
            "threshold": 0,
            "units": "score_delta",
        },
        "provenance": (
            "Sealed against parent commit " + PARENT_COMMIT + " before any "
            "SELECT-005 training result. BEST remains " + BEST_NAME + " "
            + BEST_SHA256 + "."
        ),
        "schema": THRESHOLD_SCHEMA,
        "sealed": True,
        "state": AUTHORIZATION_STATE,
        "threshold_authorization_json_schema_exists": True,
        "training_launch_authorized": False,
    }


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def apply_decision(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply the sealed rule. A failed guardrail vetoes a primary gain."""
    gates = []
    for name in REQUIRED_METRICS:
        if name not in control or name not in candidate:
            gates.append({"metric": name, "pass": False, "reason": "MISSING"})
            continue
        left = _finite_number(control[name])
        right = _finite_number(candidate[name])
        if left is None or right is None:
            gates.append({"metric": name, "pass": False, "reason": "NON_COMPUTABLE"})
            continue
        delta = right - left
        if name == PRIMARY_METRIC:
            ok = delta > 0.0
            reason = "PASS" if ok else "PRIMARY_NOT_STRICT"
        else:
            ok = delta >= 0.0
            reason = "PASS" if ok else "PRESERVATION_DEGRADED"
        gates.append(
            {
                "delta": delta,
                "metric": name,
                "pass": ok,
                "reason": reason,
            }
        )
    passed = all(gate["pass"] for gate in gates)
    return {
        "compensation": False,
        "gates": gates,
        "outcome": "PASS" if passed else "FAIL",
        "pass": passed,
    }


def semantic_errors(payload: Mapping[str, Any]) -> list[str]:
    """Schema failures and policy failures stay distinguishable by prefix."""
    errors = [f"schema: {item}" for item in threshold_schema_errors(payload)]
    if payload.get("experiment_id") != EXPERIMENT_ID:
        errors.append("experiment_id is not SELECT-005")
    if payload.get("sealed") is not True:
        errors.append("authorization is not sealed")
    if payload.get("authorization_state") != AUTHORIZATION_STATE:
        errors.append("authorization_state is not SEALED")
    if payload.get("training_launch_authorized") is not False:
        errors.append("training launch is not false")
    if payload.get("inherited_from_select_004") is not False:
        errors.append("SELECT-004 inheritance is not false")
    if payload.get("not_seed_morph78") is not True:
        errors.append("baseline is not marked distinct from seed-morph78")
    if payload.get("comparison_baseline") != COMPARISON_BASELINE:
        errors.append("comparison baseline is not the SELECT-005 control arm")
    if payload.get("preregistration_sha256") != PREREGISTRATION_SHA256:
        errors.append("preregistration sha256 does not match the sealed schedule")
    thresholds = payload.get("decision_thresholds")
    if not isinstance(thresholds, dict):
        errors.append("decision_thresholds is absent")
        thresholds = {}
    for name in REQUIRED_METRICS:
        if name not in thresholds:
            errors.append(f"missing threshold {name}")
            continue
        if thresholds[name] is None:
            errors.append(f"null threshold {name}")
        elif thresholds[name] != 0:
            errors.append(f"threshold {name} is not the sealed zero")
    metrics = payload.get("metrics")
    if not isinstance(metrics, list):
        errors.append("metrics are absent")
        metrics = []
    by_name = {
        item.get("metric"): item
        for item in metrics
        if isinstance(item, dict)
    }
    for name in REQUIRED_METRICS:
        item = by_name.get(name)
        if not isinstance(item, dict):
            errors.append(f"missing metric entry {name}")
            continue
        if item.get("numeric_threshold") is None:
            errors.append(f"null numeric_threshold {name}")
        expected = "GT" if name == PRIMARY_METRIC else "GE"
        if item.get("operator") != expected:
            errors.append(f"operator for {name} is not {expected}")
        if item.get("comparison_basis") != "candidate_minus_control":
            errors.append(f"comparison basis for {name} is not candidate_minus_control")
    primary = payload.get("primary_metric")
    if not isinstance(primary, dict) or primary.get("operator") != "GT":
        errors.append("primary operator is not GT")
    if isinstance(primary, dict) and primary.get("equality") != "FAIL":
        errors.append("primary equality is not FAIL")
    rule = payload.get("decision_rule")
    if not isinstance(rule, dict) or rule.get("compensation") is not False:
        errors.append("preservation metrics can be compensated")
    if isinstance(rule, dict) and rule.get("frozen_before_training") is not True:
        errors.append("thresholds are not marked frozen before training")
    for name, foreign in SELECT_004_FLOORS.items():
        if isinstance(thresholds, dict) and thresholds.get(name) == foreign:
            errors.append(f"SELECT-004 floor copied for {name}")
    return errors


def schema_validation_report(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    body = sealed_authorization() if payload is None else payload
    errors = threshold_schema_errors(body)
    return {
        "errors": errors,
        "mutated": False,
        "result": "PASS" if not errors else "FAIL",
        "schema": THRESHOLD_SCHEMA,
        "schema_sha256": SCHEMA_SHA256,
    }


def semantic_validation_report(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    body = sealed_authorization() if payload is None else payload
    errors = semantic_errors(body)
    schema_hit = any(item.startswith("schema:") for item in errors)
    policy = [item for item in errors if not item.startswith("schema:")]
    if errors and schema_hit and not policy:
        result = "SCHEMA_FAIL"
    elif policy:
        result = "FAIL"
    else:
        result = "PASS"
    return {"errors": errors, "result": result}


def derivation_report() -> dict[str, Any]:
    """Why each zero is the threshold, and why SELECT-004's numbers are not."""
    payload = sealed_authorization()
    return {
        "experiment_id": EXPERIMENT_ID,
        "inherited_from_select_004": False,
        "metrics": payload["metrics"],
        "rejected_select_004_floors": SELECT_004_FLOORS,
        "select_004_not_copied_because": (
            "Those floors are allowed drops versus seed-morph78 on "
            "SELECT-004 reserve counts. SELECT-005 compares its candidate "
            "with its control and has no sealed reserve count."
        ),
        "transition": TRANSITION,
    }


def authorization_sha256() -> str:
    return sha256_text(canonical_json(sealed_authorization()))
