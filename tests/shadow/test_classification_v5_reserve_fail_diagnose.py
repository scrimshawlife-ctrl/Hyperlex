"""Unit tests for V5 reserve-fail generalization diagnosis contracts."""

from __future__ import annotations

from hyperlexical.classification_v5_reserve_fail_diagnose import (
    OOD_RULE,
    PRESERVATION,
    classify_distribution,
    decide_generalization_diagnosis,
    next_action_for_diagnosis,
    route_none,
    route_present,
    route_uncertain,
)
from hyperlexical.holdout_guard import normalized_text_sha256


def test_preservation_rejects_optimization_reuse():
    assert PRESERVATION["V5_PROMOTION_RESULT"] == "RESERVE_FAIL"
    assert PRESERVATION["production_promotion"] == "REJECTED"
    assert PRESERVATION["reuse_as_train"] is False
    assert PRESERVATION["retune_thresholds"] is False
    assert PRESERVATION["rebuild_index"] is False


def test_ood_rule_preregistered_bands():
    assert classify_distribution(OOD_RULE["in_distribution_min"]) == "IN_DISTRIBUTION"
    assert (
        classify_distribution(OOD_RULE["near_distribution_min"]) == "NEAR_DISTRIBUTION"
    )
    assert classify_distribution(OOD_RULE["near_distribution_min"] - 0.01) == (
        "OUT_OF_DISTRIBUTION"
    )


def test_routing_labels():
    assert route_present(0.9, 0.8, "EVIDENCE_PRESENT") == "CORRECT_PRESENT"
    assert route_present(0.2, 0.9, "NO_EVIDENCE") == "BLOCKED_AT_GATE1"
    assert route_present(0.9, 0.2, "UNCERTAIN") == "PASSED_GATE1_REJECTED_GATE2"
    assert route_none("NO_EVIDENCE") == "CORRECT_NONE"
    assert route_none("UNCERTAIN") == "LEAKED_GATE1_TO_UNCERTAIN"
    assert route_none("EVIDENCE_PRESENT") == "LEAKED_GATE1_TO_PRESENT"
    assert route_uncertain("UNCERTAIN") == "CORRECT_UNCERTAIN"
    assert route_uncertain("NO_EVIDENCE") == "BLOCKED_AS_NONE"
    assert route_uncertain("EVIDENCE_PRESENT") == "PROMOTED_PRESENT"


def test_diagnosis_prefers_stage_a_surface_when_stage_a_collapses():
    payload = decide_generalization_diagnosis(
        stage_a_val={
            "false_entry": 0.0423,
            "PRESENT_recall": 0.7049,
            "NONE_recall": 0.9089,
        },
        stage_a_reserve={
            "false_entry": 0.0984,
            "PRESENT_recall": 0.371,
            "NONE_recall": 0.574,
        },
        stage_b_val={"family_emission_precision": 0.82, "top1_accuracy": 0.55},
        stage_b_reserve_correct_present={
            "family_emission_precision": 0.80,
            "top1_accuracy": 0.50,
            "n_correct_stage_a_present": 40,
        },
        representation_reserve={
            "distribution_class_counts": {
                "IN_DISTRIBUTION": 100,
                "NEAR_DISTRIBUTION": 80,
                "OUT_OF_DISTRIBUTION": 70,
            }
        },
    )
    assert payload["diagnosis"] in {
        "STAGE_A_GENERALIZATION_FAILURE",
        "RESERVE_DISTRIBUTION_MISMATCH",
        "MIXED_V5_GENERALIZATION_FAILURE",
        "COMPOUND_GENERALIZATION_FAILURE",
    }
    assert payload["remediation"] == "NEW_STAGE_A_TRAINING_SURFACE"
    assert "NEW_STAGE_A_TRAINING_SURFACE" in next_action_for_diagnosis(payload)
    assert "0.75/0.50" in next_action_for_diagnosis(payload)


def test_identity_helper_stable():
    assert len(normalized_text_sha256("diagnose fixture")) == 64
