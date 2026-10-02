"""CPU tests for REASSESS_V6_FUNCTION_PRODUCT_REQUIREMENT."""

from __future__ import annotations

from hyperlexical.classification_v6_function_product_requirement import (
    BASELINE_REP_V3,
    FUNCTION_VOCAB,
    PER_FUNCTION_EVIDENCE,
    PHASE_RULE,
    build_product_requirement_receipt,
    classify_product_disposition,
    core_without_function_metrics,
    product_requirement_contract,
    recommend_function_disposition,
)


def test_contract_is_decision_only():
    c = product_requirement_contract()
    assert c["PHASE_RULE"] == PHASE_RULE
    assert "train_another_function_model" in c["forbidden"]
    assert "rescore_QUAL" in c["forbidden"]
    assert c["QUALIFICATION_RESCORED"] is False
    assert c["parent"]["PRAGMATIC_OBJECTIVE"] == "V6_PRAGMATIC_OBJECTIVE_NOT_SUPPORTED"
    assert len(c["function_vocab"]) == len(FUNCTION_VOCAB) == 4


def test_core_without_function_and_dispositions():
    core = core_without_function_metrics(
        domain_macro=BASELINE_REP_V3["DOMAIN_macro_f1"],
        mediation_macro=BASELINE_REP_V3["MEDIATION_macro_f1"],
        zero_fp=BASELINE_REP_V3["zero_label_false_positive_rate"],
        zero_exact=BASELINE_REP_V3["zero_label_exact_rejection"],
    )
    assert core["FUNCTION_excluded_from_system_macro"] is True
    assert abs(core["core_system_macro_f1"] - 0.34844) < 1e-3
    assert core["core_vs_three_axis_delta"] > 0

    per = {
        lab: recommend_function_disposition(ev)
        for lab, ev in PER_FUNCTION_EVIDENCE.items()
    }
    assert all(per[lab]["disposition"] != "KEEP_REQUIRED" for lab in FUNCTION_VOCAB)

    decision = classify_product_disposition(
        {
            "per_function_dispositions": per,
            "core_without_function": core,
            "none_preserved": True,
            "ceiling_class": "TEXT_SIGNAL_CEILING",
            "pragmatic_outcome": "V6_PRAGMATIC_OBJECTIVE_NOT_SUPPORTED",
            "primitive_cue_recovery_lift": 0.013,
            "baseline_FUNCTION_macro_f1": BASELINE_REP_V3["FUNCTION_macro_f1"],
        }
    )
    assert decision["PRODUCT_DISPOSITION"] == "FUNCTION_RETAIN_OPTIONAL"
    assert (
        decision["NEXT_ACTION"]
        == "HARDEN_V6_CORE_PRODUCT_WITHOUT_REQUIRED_FUNCTION"
    )
    assert "function" not in decision["revised_v6_output_contract"]["required_outputs"]
    assert decision["revised_v6_output_contract"]["FUNCTION_blocks_release"] is False
    assert decision["core_viable"] is True

    receipt = build_product_requirement_receipt(
        {
            "per_function_dispositions": per,
            "core_without_function": core,
            "none_preserved": True,
            "preserved_research_findings": ["TEXT_SIGNAL_CEILING"],
        },
        sealed_at="2026-10-02T00:00:00Z",
    )
    assert receipt["FUNCTION_MODEL_TRAINED"] is False
    assert receipt["SYSTEM_FUNCTION_PRODUCT_REQUIREMENT_RECEIPT_SHA256"]
