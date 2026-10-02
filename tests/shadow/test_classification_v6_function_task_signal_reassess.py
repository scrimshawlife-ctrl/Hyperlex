"""CPU tests for REASSESS_V6_FUNCTION_TASK_SIGNAL contracts."""

from __future__ import annotations

from hyperlexical.classification_v6_function_task_signal_reassess import (
    FUNCTION_VOCAB,
    PHASE_RULE,
    build_reassess_receipt,
    classify_ceiling,
    classify_function_signal,
    derive_diagnosis,
    reassess_contract,
)


def test_reassess_contract_is_diagnostic_only():
    c = reassess_contract()
    assert c["PHASE_RULE"] == PHASE_RULE
    assert "design_another_function_head" in c["forbidden"]
    assert "tune_thresholds" in c["forbidden"]
    assert c["QUALIFICATION_USED_FOR_OPTIMIZATION"] is False
    assert c["parent"]["outcome"] == "V6_FUNCTION_PREDICTION_PARTIAL"
    assert len(c["function_vocab"]) == len(FUNCTION_VOCAB) == 4


def test_signal_and_ceiling_classifiers():
    assert (
        classify_function_signal(
            {
                "train_support": 20,
                "rep_support": 5,
                "old_head_f1": 0.1,
                "independent_f1": 0.1,
            }
        )
        == "INSUFFICIENT_SUPPORT"
    )
    assert (
        classify_function_signal(
            {
                "train_support": 80,
                "rep_support": 40,
                "old_head_f1": 0.25,
                "independent_f1": 0.24,
                "adjacent_overlap_rate": 0.5,
            }
        )
        == "SEMANTICALLY_OVERLAPPING"
    )
    assert (
        classify_function_signal(
            {
                "train_support": 80,
                "rep_support": 40,
                "old_head_f1": 0.28,
                "independent_f1": 0.27,
                "pragmatic_or_context_share": 0.55,
                "consensus_fail_share_among_gold": 0.5,
            }
        )
        == "CONTEXT_SENSITIVE"
    )
    ceiling = classify_ceiling(
        {
            "formulation_function_macros": {
                "OLD_SHARED_HEAD": 0.296,
                "INDEPENDENT_BINARY_VERIFIERS": 0.294,
                "HYBRID_VERIFIER": 0.28,
                "FUNCTION_SEMANTIC_MATCHING": 0.20,
            },
            "mean_consensus_fail_share": 0.42,
            "mean_pragmatic_share": 0.48,
            "diversity_adequate": True,
        }
    )
    assert ceiling == "TEXT_SIGNAL_CEILING"


def test_derive_partial_pragmatic_next():
    per = {
        lab: {
            "signal_class": (
                "CONTEXT_SENSITIVE"
                if i < 2
                else "WEAK_BUT_LEARNABLE"
            )
        }
        for i, lab in enumerate(FUNCTION_VOCAB)
    }
    d = derive_diagnosis(
        {
            "per_function": per,
            "ceiling_class": "TEXT_SIGNAL_CEILING",
            "task_signal_limit": True,
            "axis_structure": "latent_pragmatic_attributes",
        }
    )
    assert d["PRIMARY_DIAGNOSIS"] == "FUNCTION_TASK_SIGNAL_PARTIAL"
    assert d["NEXT_ACTION"] in {
        "REDESIGN_V6_FUNCTION_OBJECTIVE_AROUND_PRAGMATIC_SIGNAL",
        "SPLIT_V6_FUNCTIONS_BY_SIGNAL_REGIME",
    }
    receipt = build_reassess_receipt(
        {
            "per_function": per,
            "ceiling_class": "TEXT_SIGNAL_CEILING",
            "task_signal_limit": True,
            "axis_structure": "latent_pragmatic_attributes",
            "formulation_function_macros": {"OLD_SHARED_HEAD": 0.296},
        },
        reviewed_at="2026-10-02T00:00:00Z",
    )
    assert receipt["FUNCTION_HEAD_REDESIGNED"] is False
    assert receipt["SYSTEM_TASK_SIGNAL_RECEIPT_SHA256"]
