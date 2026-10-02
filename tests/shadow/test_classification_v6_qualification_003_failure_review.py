"""CPU tests for REVIEW_V6_QUALIFICATION_003_FAILURE contracts."""

from __future__ import annotations

from hyperlexical.classification_v6_qualification_003_failure_review import (
    EXPECTED_QUAL_RESULT_SHA256,
    NEXT_PHASES,
    NONE_GATE_STATUSES,
    PRIMARY_DIAGNOSES,
    REJECTED_MICRO_FIXES,
    REVIEW_RULE,
    build_review_receipt,
    classify_function_failure_mode,
    derive_diagnosis,
    review_contract,
)


def test_review_003_identity():
    c = review_contract()
    assert c["REVIEW_RULE"] == REVIEW_RULE == "REVIEW_V6_QUALIFICATION_003_FAILURE"
    assert c["QUALIFICATION_USED_FOR_OPTIMIZATION"] is False
    assert c["HUB_PUBLISH_AUTHORIZED"] is False
    assert c["RELEASE_ELIGIBLE"] is False
    assert c["MODEL_WIDE_BEST_MUTATED"] is False
    assert (
        c["expected"]["qual_result_sha256"]
        == EXPECTED_QUAL_RESULT_SHA256
        == "b560dac2a8f80f45c6213dcd2ba25acdb2e0b7dde786da3ee0a5d6e3231ae724"
    )
    assert c["expected"]["package_sha256"].startswith("8ed1a4d4")
    assert c["expected"]["n_rows"] == 1151
    assert "retune_ANY_LABEL_threshold" in c["forbidden"]
    assert "modify_NONE_rejection" in c["forbidden"]
    assert all(v is False for v in REJECTED_MICRO_FIXES.values())
    assert set(PRIMARY_DIAGNOSES) == set(c["primary_diagnoses"])
    assert "EXPAND_V6_FUNCTION_DIVERSITY_AND_POSITIVE_REPRESENTATION" in NEXT_PHASES
    assert "NONE_GATE_FROZEN_RETAIN" in NONE_GATE_STATUSES


def test_function_failure_mode_mixed():
    mode = classify_function_failure_mode(
        {
            "positive_false_reject": {"gate_reject_rate_on_positives": 0.31},
            "function_failure": {
                "gate_reject_rate_on_function_gold": 0.48,
                "admitted_mean_recall": 0.02,
                "qual_to_rep_support_ratio": 0.22,
                "length_shift_severe": True,
                "qual_function_wiki_none_share": 0.30,
            },
        }
    )
    assert mode == "MIXED"


def test_function_failure_mode_gate_induced():
    mode = classify_function_failure_mode(
        {
            "positive_false_reject": {"gate_reject_rate_on_positives": 0.50},
            "function_failure": {
                "gate_reject_rate_on_function_gold": 0.55,
                "admitted_mean_recall": 0.40,
                "qual_to_rep_support_ratio": 0.80,
                "length_shift_severe": False,
                "qual_function_wiki_none_share": 0.05,
            },
        }
    )
    assert mode == "GATE_INDUCED"


def test_derive_mixed_positive_semantic_and_freeze_none():
    audit = {
        "positive_false_reject": {
            "gate_reject_rate_on_positives": 0.312,
            "final_empty_rate_on_positives": 0.503,
            "post_admission_empty_share_of_final_empty": 0.38,
        },
        "function_failure": {
            "mode": "MIXED",
            "gate_reject_rate_on_function_gold": 0.48,
            "admitted_mean_recall": 0.02,
            "qual_to_rep_support_ratio": 0.22,
            "length_shift_severe": True,
            "qual_function_wiki_none_share": 0.30,
        },
        "positive_representativeness": {
            "class": "POSITIVE_REPRESENTATIVENESS_PARTIAL"
        },
        "representation_vs_head": {"class": "HEAD_GENERALIZATION_FAILURE"},
        "function_learnability": {"class": "UNDERREPRESENTED"},
        "none_gate": {"operating_gates_pass": True},
    }
    d = derive_diagnosis(audit)
    assert d["PRIMARY_DIAGNOSIS"] == "MIXED_POSITIVE_SEMANTIC_GENERALIZATION_FAILURE"
    assert d["NONE_GATE_STATUS"] == "NONE_GATE_FROZEN_RETAIN"
    assert (
        d["NEXT_ACTION"]
        == "EXPAND_V6_FUNCTION_DIVERSITY_AND_POSITIVE_REPRESENTATION"
    )
    receipt = build_review_receipt(audit, reviewed_at="2026-10-02T00:00:00Z")
    assert receipt["PRIMARY_DIAGNOSIS"] == d["PRIMARY_DIAGNOSIS"]
    assert receipt["NONE_GATE_STATUS"] == "NONE_GATE_FROZEN_RETAIN"
    assert receipt["QUALIFICATION_USED_FOR_OPTIMIZATION"] is False
    assert receipt["HUB_PUBLISH_AUTHORIZED"] is False
    assert receipt["MODEL_WIDE_BEST_MUTATED"] is False
    assert receipt["SYSTEM_REVIEW_RECEIPT_SHA256"]
    assert all(v is False for v in receipt["REJECTED_MICRO_FIXES"].values())


def test_derive_gate_primary_when_post_admit_low():
    audit = {
        "positive_false_reject": {
            "gate_reject_rate_on_positives": 0.50,
            "final_empty_rate_on_positives": 0.52,
            "post_admission_empty_share_of_final_empty": 0.10,
        },
        "function_failure": {
            "mode": "GATE_INDUCED",
            "gate_reject_rate_on_function_gold": 0.55,
            "admitted_mean_recall": 0.40,
            "qual_to_rep_support_ratio": 0.80,
        },
        "positive_representativeness": {
            "class": "POSITIVE_REPRESENTATIVENESS_VALID"
        },
        "representation_vs_head": {"class": "INCONCLUSIVE_WITHOUT_GEOMETRY"},
        "function_learnability": {"class": "HUMAN_STABLE_MODEL_LEARNABLE"},
        "none_gate": {"operating_gates_pass": True},
    }
    d = derive_diagnosis(audit)
    assert d["PRIMARY_DIAGNOSIS"] == "POSITIVE_GATE_GENERALIZATION_FAILURE"
    assert (
        d["NEXT_ACTION"]
        == "HARDEN_V6_POSITIVE_ADMISSION_AND_FUNCTION_GENERALIZATION"
    )
