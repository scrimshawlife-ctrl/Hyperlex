"""CPU tests for V6 QUAL-002 failure system-review contracts."""

from __future__ import annotations

from hyperlexical.classification_v6_qualification_failure_system_review import (
    EXPECTED_QUAL_RESULT_SHA256,
    REJECTED_MICRO_FIXES,
    REVIEW_RULE,
    build_system_review_receipt,
    classify_drop,
    derive_system_diagnosis,
    review_contract,
)


def test_review_identity():
    c = review_contract()
    assert c["REVIEW_RULE"] == REVIEW_RULE
    assert c["QUALIFICATION_USED_FOR_OPTIMIZATION"] is False
    assert c["HUB_PUBLISH_AUTHORIZED"] is False
    assert c["expected"]["qual_result_sha256"] == EXPECTED_QUAL_RESULT_SHA256
    assert "retrain" in c["forbidden"]
    assert all(v is False for v in REJECTED_MICRO_FIXES.values())


def test_drop_bands():
    assert classify_drop(0.43, 0.40) == "STABLE"
    assert classify_drop(0.43, 0.32) == "MODERATE_DROP"
    assert classify_drop(0.43, 0.20) == "SEVERE_DROP"
    assert classify_drop(0.43, 0.05) == "COLLAPSED"


def test_derive_representative_overfit():
    audit = {
        "rep_representativeness": {
            "class": "REPRESENTATIVE_VALIDATION_OVERFIT",
            "rep_excluded_zero_label_rows": True,
            "qual_zero_label_share": 0.745,
        },
        "cardinality_shift": {
            "rep_domain_plus_function_n": 0,
            "qual_domain_plus_function_n": 17,
        },
        "axis_degradation": {"function_class": "COLLAPSED"},
        "semantic_geometry": {"class": "GEOMETRY_STABLE_CALIBRATION_SHIFTED"},
        "calibration_counterfactual": {"classification": "OPERATING_POINT_CONFLICT"},
        "task_signal": {"class": "TASK_SIGNAL_PARTIAL"},
        "source_shift": {"class": "SOURCE_SENSITIVE"},
        "qual_validity": {"class": "HARDER_BUT_VALID"},
    }
    d = derive_system_diagnosis(audit)
    assert d["PRIMARY_DIAGNOSIS"] == "REPRESENTATIVE_VALIDATION_OVERFIT"
    assert d["V6_DISPOSITION"] == "V6_REQUIRES_DATA_DISTRIBUTION_REDESIGN"
    assert (
        d["NEXT_ACTION"]
        == "REDESIGN_V6_REPRESENTATIVE_VALIDATION_AND_DATA_DIVERSITY"
    )
    receipt = build_system_review_receipt(audit, reviewed_at="2026-10-02T00:00:00Z")
    assert receipt["PRIMARY_DIAGNOSIS"] == "REPRESENTATIVE_VALIDATION_OVERFIT"
    assert receipt["RELEASE_ELIGIBLE"] is False
    assert receipt["TRAIN"] is False
    assert receipt["QUALIFICATION_USED_FOR_OPTIMIZATION"] is False
    assert receipt["SYSTEM_REVIEW_RECEIPT_SHA256"]
    assert all(v is False for v in receipt["REJECTED_MICRO_FIXES"].values())
