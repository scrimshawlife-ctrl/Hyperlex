"""CPU tests for V6 representative-validation redesign contracts."""

from __future__ import annotations

from hyperlexical.classification_v6_representative_validation_redesign import (
    FORBIDDEN_FILTERS,
    PHASE_RULE,
    REP_V2_ZERO_LABEL_SHARE_RANGE,
    build_redesign_receipt,
    classify_remaining_model_failure,
    classify_representativeness_repair,
    decide_next_action,
    in_range,
    redesign_contract,
)


def test_redesign_contract_forbids_usable_filter():
    c = redesign_contract()
    assert c["PHASE_RULE"] == PHASE_RULE
    assert "usable()" in FORBIDDEN_FILTERS
    assert c["frozen_package"]["retrain"] is False
    assert c["historical_qual"]["row_reuse_forbidden"] is True
    assert c["historical_qual"]["new_qualification_surface"] is False
    assert in_range(0.65, *REP_V2_ZERO_LABEL_SHARE_RANGE)


def test_representativeness_repair_not_old_score():
    replay = {
        "system_macro_f1": 0.22,
        "FUNCTION_macro_f1": 0.22,
        "zero_label_false_positive_rate": 0.78,
        "positive_only_system_macro_f1": 0.41,
        "n_domain_plus_function": 6,
        "co_label_performance": {"domain_plus_function_system_macro": 0.33},
    }
    qual = {
        "system_macro_f1": 0.1885,
        "FUNCTION_macro_f1": 0.059,
        "zero_label_false_positive_rate": 0.648,
    }
    repair = classify_representativeness_repair(
        rep_audit_pass=True, replay=replay, qual_aggregate=qual
    )
    assert repair["REPRESENTATIVENESS_REPAIRED"] is True
    assert repair["recovered_old_usable_rep_score"] is False
    rem = classify_remaining_model_failure(replay)
    assert rem["REMAINING_MODEL_FAILURE"] == "NONE_REJECTION_FAILURE"
    assert (
        decide_next_action(
            representativeness_repaired=True,
            remaining_failure=rem["REMAINING_MODEL_FAILURE"],
        )
        == "HARDEN_V6_NONE_REJECTION_UNDER_FROZEN_ENCODER"
    )
    receipt = build_redesign_receipt(
        {
            "PHASE_RULE": PHASE_RULE,
            "REPRESENTATIVENESS_REPAIRED": True,
            "REMAINING_MODEL_FAILURE": rem["REMAINING_MODEL_FAILURE"],
        }
    )
    assert receipt["MODEL_WIDE_BEST_MUTATED"] is False
    assert receipt["V6_REPRESENTATIVE_VALIDATION_REDESIGN_RECEIPT_SHA256"]
