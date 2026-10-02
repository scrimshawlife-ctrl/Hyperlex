"""CPU tests for V6 QUAL-003 one-shot execute contracts."""

from __future__ import annotations

from hyperlexical.classification_v6_qualification_execute_003 import (
    EXPECTED_N_ROWS,
    EXPECTED_PACKAGE_SHA256,
    EXPECTED_SEAL_SHA256,
    PHASE_RULE,
    QUALIFICATION_ID,
    REP_REFERENCE_SYSTEM_MACRO_F1,
    classify_retention,
    decide_disposition,
    evaluate_operating_gates,
    exact_int_equals,
    execute_contract,
)


def test_execute_003_identity():
    c = execute_contract()
    assert c["PHASE_RULE"] == PHASE_RULE == "EXECUTE_V6_QUALIFICATION_003_ONCE"
    assert c["QUALIFICATION_ID"] == QUALIFICATION_ID == "HYPERLEX_V6_QUALIFICATION_003"
    assert c["expected"]["seal_sha256"] == EXPECTED_SEAL_SHA256
    assert (
        c["expected"]["package_sha256"]
        == EXPECTED_PACKAGE_SHA256
        == "8ed1a4d45d37a4cfb1ad12c0c50fd37007daa772f3cdfee35cdc454055c3699a"
    )
    assert c["expected"]["n_rows"] == EXPECTED_N_ROWS == 1151
    assert c["HUB_PUBLISH_AUTHORIZED"] is False
    assert c["gates"]["system_macro_f1_min"] == 0.30
    assert c["gates"]["zero_label_false_positive_rate_max"] == 0.35
    assert c["gates"]["zero_label_exact_rejection_min"] == 0.50
    assert c["gates"]["positive_only_system_macro_f1_min"] == 0.30
    assert "adjust_ANY_LABEL_threshold" in c["forbidden"]
    assert c["pointer_policy"]["MODEL_WIDE_BEST"] == "UNCHANGED"


def test_operating_gates_and_disposition():
    ok = evaluate_operating_gates(
        system_macro_f1=0.35,
        hierarchy_violation=0.01,
        axis_macros={"domain": 0.3, "function": 0.2, "mediation": 0.15},
        zero_label_false_positive_rate=0.20,
        zero_label_exact_rejection=0.70,
        positive_only_system_macro_f1=0.35,
    )
    assert ok["pass"] is True
    fail_sys = evaluate_operating_gates(
        system_macro_f1=0.25,
        hierarchy_violation=0.0,
        axis_macros={"domain": 0.3, "function": 0.2, "mediation": 0.15},
        zero_label_false_positive_rate=0.10,
        zero_label_exact_rejection=0.90,
        positive_only_system_macro_f1=0.40,
    )
    assert fail_sys["pass"] is False
    fail_zero = evaluate_operating_gates(
        system_macro_f1=0.40,
        hierarchy_violation=0.0,
        axis_macros={"domain": 0.3, "function": 0.2, "mediation": 0.15},
        zero_label_false_positive_rate=0.50,
        zero_label_exact_rejection=0.90,
        positive_only_system_macro_f1=0.40,
    )
    assert fail_zero["pass"] is False
    assert decide_disposition(preflight_ok=False, execution_ok=True, gate_pass=True)[
        "QUALIFICATION_DISPOSITION"
    ] == "V6_QUALIFICATION_003_INVALID"
    assert decide_disposition(preflight_ok=True, execution_ok=True, gate_pass=True)[
        "NEXT_ACTION"
    ] == "PREPARE_HYPERLEX_V6_RELEASE_CANDIDATE"
    assert decide_disposition(preflight_ok=True, execution_ok=True, gate_pass=False)[
        "NEXT_ACTION"
    ] == "REVIEW_V6_QUALIFICATION_003_FAILURE"


def test_retention_and_zero_equals():
    strong = classify_retention(0.35, rep_macro=REP_REFERENCE_SYSTEM_MACRO_F1)
    assert strong["band"] in {"STRONG_RETENTION", "MODERATE_RETENTION"}
    assert exact_int_equals(0, 0) is True
    assert exact_int_equals(None, 0) is False
