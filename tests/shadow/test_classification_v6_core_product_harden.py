"""CPU tests for HARDEN_V6_CORE_PRODUCT_WITHOUT_REQUIRED_FUNCTION."""

from __future__ import annotations

from hyperlexical.classification_v6_core_product_harden import (
    CORE_QUALIFICATION_GATES,
    PHASE_RULE,
    build_core_harden_receipt,
    classify_core_harden_outcome,
    core_output_contract,
    core_product_contract,
    evaluate_core_gates,
)


def test_core_contract_excludes_function_from_pass_fail():
    c = core_product_contract()
    assert c["PHASE_RULE"] == PHASE_RULE
    assert "function" not in c["output_contract"]["required_outputs"]
    assert c["output_contract"]["FUNCTION_blocks_release"] is False
    assert CORE_QUALIFICATION_GATES["FUNCTION_in_pass_fail"] is False
    assert "score_QUAL_002" in c["forbidden"]
    assert "score_QUAL_003" in c["forbidden"]
    assert "include_FUNCTION_in_core_pass_fail" in c["forbidden"]
    out = core_output_contract()
    assert out["FUNCTION_reporting"] == "ADVISORY_ONLY_NON_BLOCKING"
    assert "function.memetic_form" in out["research_only"]


def test_gates_and_harden_outcomes():
    good = {
        "core_system_macro_f1": 0.348,
        "DOMAIN_macro_f1": 0.355,
        "MEDIATION_macro_f1": 0.342,
        "zero_label_false_positive_rate": 0.088,
        "zero_label_exact_rejection": 0.912,
        "mean_predicted_labels_on_zero_gold": 0.15,
        "hierarchy_violation_rate": 0.002,
    }
    assert evaluate_core_gates(good)["pass"] is True
    bad = dict(good, DOMAIN_macro_f1=0.10)
    assert evaluate_core_gates(bad)["pass"] is False

    hardened = classify_core_harden_outcome(
        {
            "package_ok": True,
            "cold_load_ok": True,
            "round_trip_ok": True,
            "encoder_immutable": True,
            "rep_gate_eval": {"pass": True},
            "dev_gate_eval": {"pass": True},
            "function_advisory_non_blocking": True,
        }
    )
    assert hardened["OUTCOME"] == "V6_CORE_PRODUCT_HARDENED"
    assert (
        hardened["NEXT_ACTION"]
        == "BUILD_AND_SEAL_FRESH_V6_CORE_QUALIFICATION_SURFACE"
    )

    blocked = classify_core_harden_outcome(
        {
            "package_ok": False,
            "cold_load_ok": False,
            "round_trip_ok": False,
            "encoder_immutable": True,
            "rep_gate_eval": {"pass": False},
            "function_advisory_non_blocking": True,
        }
    )
    assert blocked["OUTCOME"] == "V6_CORE_PRODUCT_BLOCKED"

    receipt = build_core_harden_receipt(
        {
            "package_ok": True,
            "cold_load_ok": True,
            "round_trip_ok": True,
            "encoder_immutable": True,
            "rep_gate_eval": {"pass": True},
            "PACKAGE_SHA256": "abc",
            "function_advisory": {"role": "ADVISORY_ONLY"},
        },
        sealed_at="2026-10-02T00:00:00Z",
    )
    assert receipt["FUNCTION_REQUIRED"] is False
    assert receipt["SYSTEM_CORE_PRODUCT_HARDEN_RECEIPT_SHA256"]
