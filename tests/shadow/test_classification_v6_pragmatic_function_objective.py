"""CPU tests for REDESIGN_V6_FUNCTION_OBJECTIVE_AROUND_PRAGMATIC_SIGNAL."""

from __future__ import annotations

from hyperlexical.classification_v6_pragmatic_function_objective import (
    FUNCTION_VOCAB,
    PHASE_RULE,
    PRIMITIVE_VOCAB,
    build_pragmatic_receipt,
    classify_pragmatic_outcome,
    classify_row_annotation_status,
    derive_functions_from_primitives,
    detect_primitive_cues,
    pragmatic_contract,
)


def test_contract_freezes_architecture():
    c = pragmatic_contract()
    assert c["PHASE_RULE"] == PHASE_RULE
    assert "change_encoder" in c["forbidden"]
    assert "another_direct_function_head" in c["forbidden"]
    assert "tune_on_QUAL" in c["forbidden"]
    assert c["QUALIFICATION_USED_FOR_OPTIMIZATION"] is False
    assert len(c["primitive_vocab"]) == len(PRIMITIVE_VOCAB) == 5
    assert len(c["function_vocab"]) == len(FUNCTION_VOCAB) == 4
    assert c["parent"]["PRIMARY_DIAGNOSIS"] == "FUNCTION_TASK_SIGNAL_PARTIAL"


def test_detect_and_derive():
    hits = detect_primitive_cues("A pejorative insult used in military combat memes.")
    assert "prag.normative_judgment" in hits
    assert "prag.hostile_force" in hits
    derived = derive_functions_from_primitives(hits, abstain=True)
    assert "function.evaluative_stance" in derived["function_labels"]
    assert "function.conflictive_force" in derived["function_labels"]

    mock_only = derive_functions_from_primitives(
        ["prag.mockery_framing"], abstain=True
    )
    assert "function.memetic_form" not in mock_only["function_labels"]
    assert "function.memetic_form" in mock_only["unresolved_functions"]


def test_annotation_status_and_outcome():
    direct = classify_row_annotation_status(
        "A pejorative term of contempt.",
        ["function.evaluative_stance"],
    )
    assert direct["status"] == "DIRECTLY_DERIVED"
    missing = classify_row_annotation_status(
        "The anchoring of the wheels of an artillery piece.",
        ["function.conflictive_force"],
    )
    assert missing["status"] == "HUMAN_RESETTLEMENT_REQUIRED"

    advance = classify_pragmatic_outcome(
        {
            "identifiability_lift": 0.25,
            "primitive_dual_agreement": 0.9,
            "function_dual_agreement": 0.5,
            "none_preserved": True,
            "derived_FUNCTION_macro_f1": 0.33,
            "baseline_FUNCTION_macro_f1": 0.296,
            "false_function_emission": 0.05,
            "baseline_false_function_emission": 0.12,
            "human_resettlement_share": 0.40,
            "cue_positive_rows": {"REP": 40},
            "selected_objective": "C_PRIMITIVE_PLUS_ABSTENTION",
        }
    )
    assert advance["OUTCOME"] in {
        "V6_PRAGMATIC_OBJECTIVE_ADVANCE",
        "V6_PRAGMATIC_OBJECTIVE_PARTIAL",
    }
    assert advance["NEXT_ACTION"] in {
        "HARDEN_V6_PRAGMATIC_FUNCTION_PIPELINE",
        "COMPLETE_V6_PRAGMATIC_PRIMITIVE_SETTLEMENT",
    }

    reject = classify_pragmatic_outcome(
        {
            "identifiability_lift": 0.01,
            "primitive_dual_agreement": 0.5,
            "function_dual_agreement": 0.5,
            "none_preserved": True,
            "derived_FUNCTION_macro_f1": 0.20,
            "baseline_FUNCTION_macro_f1": 0.296,
            "human_resettlement_share": 0.8,
            "selected_objective": None,
        }
    )
    assert reject["OUTCOME"] == "V6_PRAGMATIC_OBJECTIVE_NOT_SUPPORTED"
    assert reject["NEXT_ACTION"] == "REASSESS_V6_FUNCTION_PRODUCT_REQUIREMENT"

    receipt = build_pragmatic_receipt(
        {
            "identifiability_lift": 0.2,
            "primitive_dual_agreement": 0.85,
            "function_dual_agreement": 0.55,
            "none_preserved": True,
            "derived_FUNCTION_macro_f1": 0.28,
            "human_resettlement_share": 0.5,
            "selected_objective": "B_PRIMITIVE_PLUS_DERIVATION",
        },
        sealed_at="2026-10-02T00:00:00Z",
    )
    assert receipt["DIRECT_FUNCTION_HEAD_ADDED"] is False
    assert receipt["SYSTEM_PRAGMATIC_OBJECTIVE_RECEIPT_SHA256"]
