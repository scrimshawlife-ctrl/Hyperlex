"""Tests for V5 qualification-failure system review contracts (CPU only)."""

from __future__ import annotations

from hyperlexical.classification_v5_qualification_failure_system_review import (
    NEXT_ACTION,
    PRIMARY_REMEDIATION_PHASE,
    QUALIFICATION_SURFACE_VALIDITY,
    REJECTED_MICRO_FIXES,
    REVIEW_ID,
    REVIEW_RULE,
    SYSTEM_DIAGNOSIS,
    V5_DISPOSITION,
    build_system_review_receipt,
    derive_system_diagnosis,
)


def test_frozen_system_review_enums():
    assert REVIEW_RULE.startswith("REVIEW_V5_QUALIFICATION_FAILURE")
    assert REVIEW_ID.endswith("SYSTEM_REVIEW_001")
    assert SYSTEM_DIAGNOSIS == "MIXED_SYSTEM_GENERALIZATION_FAILURE"
    assert V5_DISPOSITION == "V5_RESEARCH_PROTOTYPE"
    assert PRIMARY_REMEDIATION_PHASE == "BUILD_REPRESENTATIVE_V6_DATA_FOUNDATION"
    assert NEXT_ACTION == PRIMARY_REMEDIATION_PHASE
    assert QUALIFICATION_SURFACE_VALIDITY == "QUALIFICATION_SURFACE_HARD_BUT_VALID"
    assert REJECTED_MICRO_FIXES["more_stage_a_threshold_tuning"] is False
    assert REJECTED_MICRO_FIXES["another_stage_b_floor_tune"] is False
    assert REJECTED_MICRO_FIXES["simply_enlarging_existing_index"] is False


def test_derive_mixed_system_failure_and_receipt():
    audit = {
        "stage_a": {
            "qualification": {
                "false_entry": 0.3153,
                "present_recall": 0.5844,
                "none_recall": 0.6847,
            }
        },
        "stage_b_independent": {
            "independent_generalization_failure": True,
            "family_precision": 0.2745,
        },
        "distribution": {
            "stage_a_shift_class": "MATERIAL_DISTRIBUTION_SHIFT",
            "stage_b_shift_class": "MATERIAL_DISTRIBUTION_SHIFT",
        },
        "stage_a_calibration": {
            "classification": "STRUCTURAL_OVERLAP",
            "any_threshold_region_rescues_primary_gates": False,
        },
        "surface_validity": {"disposition": "QUALIFICATION_SURFACE_HARD_BUT_VALID"},
        "representation": {
            "representation_class": "MIXED_REPRESENTATION_FAILURE",
            "ontology_separability": "ONTOLOGY_PARTIALLY_SEPARABLE",
        },
        "ontology_separability": "ONTOLOGY_PARTIALLY_SEPARABLE",
    }
    derived = derive_system_diagnosis(audit)
    assert derived["SYSTEM_DIAGNOSIS"] == "MIXED_SYSTEM_GENERALIZATION_FAILURE"
    assert derived["PRIMARY_REMEDIATION_PHASE"] == "BUILD_REPRESENTATIVE_V6_DATA_FOUNDATION"
    assert derived["V5_DISPOSITION"] == "V5_RESEARCH_PROTOTYPE"

    receipt = build_system_review_receipt(audit, reviewed_at="2026-10-01T00:00:00Z")
    assert receipt["SYSTEM_DIAGNOSIS"] == "MIXED_SYSTEM_GENERALIZATION_FAILURE"
    assert receipt["RELEASE_ELIGIBLE"] is False
    assert receipt["HUB_PUBLISH_AUTHORIZED"] is False
    assert receipt["TRAIN"] is False
    assert receipt["QUALIFICATION_USED_FOR_OPTIMIZATION"] is False
    assert receipt["SYSTEM_REVIEW_RECEIPT_SHA256"]
    assert all(v is False for v in receipt["REJECTED_MICRO_FIXES"].values())
