"""CPU tests for V6 NONE-rejection harden contracts."""

from __future__ import annotations

from hyperlexical.classification_v6_none_rejection_harden import (
    BASELINE_REP_POSITIVE_ONLY_MACRO_F1,
    BASELINE_REP_ZERO_FP_RATE,
    MECHANISMS,
    PHASE_RULE,
    POSITIVE_PRESERVATION_RATIO,
    build_none_rejection_receipt,
    classify_disposition,
    decide_next_action,
    none_rejection_contract,
    not_reject_everything,
    positive_preserved,
    zero_label_improved,
)


def test_contract_freezes_encoder_and_surfaces():
    c = none_rejection_contract()
    assert c["PHASE_RULE"] == PHASE_RULE
    assert c["frozen"]["encoder_mutable"] is False
    assert c["frozen"]["architecture_bakeoff"] is False
    assert c["surfaces"]["definitions_frozen"] is True
    assert c["QUAL_002"]["row_access"] is False
    assert c["MODEL_WIDE_BEST_MUTATED"] is False
    assert "LEARNED_ANY_EVIDENCE_GATE" in MECHANISMS
    assert c["acceptance"]["gates_locked_before_results"] is True
    floor = BASELINE_REP_POSITIVE_ONLY_MACRO_F1 * POSITIVE_PRESERVATION_RATIO
    assert abs(c["acceptance"]["positive_only_floor"] - floor) < 1e-12


def test_advance_requires_zero_and_positive():
    good = {
        "system_macro_f1": 0.28,
        "FUNCTION_macro_f1": 0.22,
        "zero_label_false_positive_rate": BASELINE_REP_ZERO_FP_RATE - 0.25,
        "zero_label_exact_rejection": 0.55,
        "mean_predicted_labels_on_zero_gold": 0.8,
        "positive_only_system_macro_f1": 0.40,
        "false_reject_positive_rate": 0.10,
    }
    assert zero_label_improved(good)
    assert positive_preserved(good)
    assert not_reject_everything(good)
    d = classify_disposition(good)
    assert d["DISPOSITION"] == "V6_NONE_REJECTION_ADVANCE"
    assert (
        decide_next_action(d["DISPOSITION"], good)
        == "HARDEN_V6_FULL_OPERATING_PIPELINE_AND_PREPARE_NEW_QUALIFICATION"
    )


def test_reject_everything_is_no_advance():
    bad = {
        "system_macro_f1": 0.05,
        "FUNCTION_macro_f1": 0.0,
        "zero_label_false_positive_rate": 0.0,
        "zero_label_exact_rejection": 1.0,
        "mean_predicted_labels_on_zero_gold": 0.0,
        "positive_only_system_macro_f1": 0.0,
        "false_reject_positive_rate": 1.0,
    }
    d = classify_disposition(bad)
    assert d["DISPOSITION"] == "V6_NONE_REJECTION_NO_ADVANCE"
    assert decide_next_action(d["DISPOSITION"], bad) == "REASSESS_V6_EVIDENCE_GATE_SIGNAL"
    receipt = build_none_rejection_receipt(
        {"PHASE_RULE": PHASE_RULE, "DISPOSITION": d["DISPOSITION"]}
    )
    assert receipt["MODEL_WIDE_BEST_MUTATED"] is False
    assert receipt["V6_NONE_REJECTION_HARDEN_RECEIPT_SHA256"]


def test_baseline_relative_false_reject_allows_modest_tradeoff():
    # Sealed gate candidate: huge zero-FP drop, positive-only held, FR +6pp.
    metrics = {
        "system_macro_f1": 0.3698,
        "FUNCTION_macro_f1": 0.3711,
        "zero_label_false_positive_rate": 0.0877,
        "zero_label_exact_rejection": 0.9123,
        "mean_predicted_labels_on_zero_gold": 0.145,
        "positive_only_system_macro_f1": 0.4158,
        "false_reject_positive_rate": 0.4164,
    }
    assert zero_label_improved(metrics)
    assert positive_preserved(metrics)
    assert not_reject_everything(metrics)
    d = classify_disposition(metrics)
    assert d["DISPOSITION"] == "V6_NONE_REJECTION_ADVANCE"
