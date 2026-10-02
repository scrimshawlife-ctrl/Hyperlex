"""CPU tests for REDESIGN_V6_FUNCTION_PREDICTION contracts."""

from __future__ import annotations

from hyperlexical.classification_v6_function_prediction_redesign import (
    BASELINE_REP_V3,
    FORMULATIONS,
    FUNCTION_VOCAB,
    PHASE_RULE,
    build_redesign_receipt,
    classify_outcome,
    redesign_contract,
    select_best_on_dev,
)


def test_redesign_contract_freezes_domain_mediation():
    c = redesign_contract()
    assert c["PHASE_RULE"] == PHASE_RULE
    assert c["frozen"]["ontology_changed"] is False
    assert "retrain_DOMAIN" in c["forbidden"]
    assert "retrain_MEDIATION" in c["forbidden"]
    assert "modify_NONE_gate" in c["forbidden"]
    assert "tune_on_QUAL" in c["forbidden"]
    assert set(FORMULATIONS) == set(c["formulations"])
    assert len(c["function_vocab"]) == 4
    assert c["baseline_REP_V3"]["FUNCTION_macro_f1"] == BASELINE_REP_V3["FUNCTION_macro_f1"]
    assert c["NO_FUNCTION_semantics"].startswith("absence_of_all")
    assert c["QUALIFICATION_USED_FOR_OPTIMIZATION"] is False


def test_select_best_on_dev():
    sel = select_best_on_dev(
        [
            {
                "formulation": "FUNCTION_SEMANTIC_MATCHING",
                "FUNCTION_macro_f1": 0.20,
                "system_macro_f1": 0.30,
                "positive_only_system_macro_f1": 0.30,
            },
            {
                "formulation": "INDEPENDENT_BINARY_VERIFIERS",
                "FUNCTION_macro_f1": 0.33,
                "system_macro_f1": 0.34,
                "positive_only_system_macro_f1": 0.36,
            },
            {
                "formulation": "HYBRID_VERIFIER",
                "FUNCTION_macro_f1": 0.31,
                "system_macro_f1": 0.35,
                "positive_only_system_macro_f1": 0.37,
            },
        ]
    )
    assert sel["selected"] == "INDEPENDENT_BINARY_VERIFIERS"


def test_classify_advance_and_no_advance():
    per = {lab: {"f1": 0.25, "support": 40} for lab in FUNCTION_VOCAB}
    adv = classify_outcome(
        candidate={
            "FUNCTION_macro_f1": 0.35,
            "system_macro_f1": 0.34,
            "positive_only_system_macro_f1": 0.37,
            "zero_label_false_positive_rate": 0.10,
            "zero_label_exact_rejection": 0.90,
            "per_label_function": per,
        }
    )
    assert adv["OUTCOME"] == "V6_FUNCTION_PREDICTION_ADVANCE"
    assert (
        adv["NEXT_ACTION"]
        == "HARDEN_V6_FULL_OPERATING_PIPELINE_WITH_REDESIGNED_FUNCTION"
    )
    no = classify_outcome(
        candidate={
            "FUNCTION_macro_f1": 0.20,
            "system_macro_f1": 0.30,
            "positive_only_system_macro_f1": 0.30,
            "zero_label_false_positive_rate": 0.10,
            "zero_label_exact_rejection": 0.90,
            "per_label_function": per,
        }
    )
    assert no["OUTCOME"] == "V6_FUNCTION_PREDICTION_NO_ADVANCE"
    assert no["NEXT_ACTION"] == "REASSESS_V6_FUNCTION_TASK_SIGNAL"
    receipt = build_redesign_receipt(
        {"OUTCOME": no["OUTCOME"], "NEXT_ACTION": no["NEXT_ACTION"]},
        sealed_at="2026-10-02T00:00:00Z",
    )
    assert receipt["DOMAIN_HEAD_MUTATED"] is False
    assert receipt["MEDIATION_HEAD_MUTATED"] is False
    assert receipt["SYSTEM_FUNCTION_REDESIGN_RECEIPT_SHA256"]
