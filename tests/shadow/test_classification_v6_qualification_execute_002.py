"""CPU tests for V6 QUAL-002 one-shot execute contracts."""

from __future__ import annotations

from hyperlexical.classification_v6_qualification_execute_002 import (
    EXPECTED_N_ROWS,
    EXPECTED_PACKAGE_SHA256,
    EXPECTED_SEAL_SHA256,
    PHASE_RULE,
    QUALIFICATION_ID,
    REP_REFERENCE_SYSTEM_MACRO_F1,
    axis_collapse_detected,
    classify_qual_label,
    classify_retention,
    decide_disposition,
    evaluate_gates,
    exact_int_equals,
    execute_contract,
)


def test_execute_identity():
    c = execute_contract()
    assert c["PHASE_RULE"] == PHASE_RULE == "EXECUTE_V6_FRESH_QUALIFICATION_ONCE"
    assert c["QUALIFICATION_ID"] == QUALIFICATION_ID
    assert c["expected"]["seal_sha256"] == EXPECTED_SEAL_SHA256
    assert c["expected"]["package_sha256"] == EXPECTED_PACKAGE_SHA256
    assert c["expected"]["n_rows"] == EXPECTED_N_ROWS
    assert c["HUB_PUBLISH_AUTHORIZED"] is False
    assert c["gates"]["system_macro_f1_min"] == 0.30
    assert c["gates"]["hierarchy_violation_max"] == 0.05
    assert "retrain" in c["forbidden"]
    assert c["pointer_policy"]["MODEL_WIDE_BEST"] == "UNCHANGED"


def test_retention_bands():
    strong = classify_retention(0.40, rep_macro=REP_REFERENCE_SYSTEM_MACRO_F1)
    assert strong["band"] == "STRONG_RETENTION"
    mod = classify_retention(0.32, rep_macro=REP_REFERENCE_SYSTEM_MACRO_F1)
    assert mod["band"] == "MODERATE_RETENTION"
    sev = classify_retention(0.20, rep_macro=REP_REFERENCE_SYSTEM_MACRO_F1)
    assert sev["band"] == "SEVERE_GENERALIZATION_DROP"
    assert strong["hard_gate"] is False


def test_gates_and_disposition():
    ok = evaluate_gates(
        system_macro_f1=0.35,
        hierarchy_violation=0.01,
        axis_macros={"domain": 0.3, "function": 0.2, "mediation": 0.15},
    )
    assert ok["pass"] is True
    assert not axis_collapse_detected(ok["gates"]["no_material_axis_collapse"]["axis_macros"])
    fail = evaluate_gates(
        system_macro_f1=0.25,
        hierarchy_violation=0.0,
        axis_macros={"domain": 0.3, "function": 0.2, "mediation": 0.15},
    )
    assert fail["pass"] is False
    collapse = evaluate_gates(
        system_macro_f1=0.40,
        hierarchy_violation=0.0,
        axis_macros={"domain": 0.3, "function": 0.05, "mediation": 0.2},
    )
    assert collapse["pass"] is False
    assert decide_disposition(preflight_ok=False, execution_ok=True, gate_pass=True)[
        "QUALIFICATION_DISPOSITION"
    ] == "V6_QUALIFICATION_INVALID"
    assert decide_disposition(preflight_ok=True, execution_ok=True, gate_pass=True)[
        "NEXT_ACTION"
    ] == "PREPARE_HYPERLEX_V6_RELEASE_CANDIDATE"
    assert decide_disposition(preflight_ok=True, execution_ok=True, gate_pass=False)[
        "NEXT_ACTION"
    ] == "REVIEW_V6_QUALIFICATION_FAILURE_AT_SYSTEM_LEVEL"


def test_label_classes():
    assert classify_qual_label(qual_f1=0.5, support=5) == "LOW_SUPPORT"
    assert classify_qual_label(qual_f1=0.01, support=20) == "FAILED"
    assert classify_qual_label(qual_f1=0.15, support=20) == "DEGRADED"
    assert classify_qual_label(qual_f1=0.4, support=20, rep_f1=0.7) == "DEGRADED"
    assert classify_qual_label(qual_f1=0.5, support=20, rep_f1=0.55) == "STABLE"


def test_exact_int_equals_accepts_zero():
    # Regression: `int(value or -1) != 0` falsely rejects sealed zeros.
    assert exact_int_equals(0, 0) is True
    assert exact_int_equals("0", 0) is True
    assert exact_int_equals(None, 0) is False
    assert exact_int_equals(1, 0) is False
    assert (0 or -1) != 0  # documents the anti-pattern this helper replaces
