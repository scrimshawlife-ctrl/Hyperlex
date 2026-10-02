"""CPU tests for HYPERLEX_V6_CORE_QUALIFICATION_001 program contracts."""

from __future__ import annotations

from hyperlexical.classification_v6_core_qualification import (
    EXPECTED_PACKAGE_SHA256,
    QUALIFICATION_ID,
    classify_failure,
    classify_retention,
    coverage_sufficient_core,
    decide_disposition,
    evaluate_core_qual_gates,
    surface_contract,
)


def test_core_qual_contract_excludes_function_and_spent_surfaces():
    assert QUALIFICATION_ID == "HYPERLEX_V6_CORE_QUALIFICATION_001"
    assert EXPECTED_PACKAGE_SHA256.startswith("035e1b7e")
    c = surface_contract()
    assert c["FUNCTION_role"] == "ADVISORY_ONLY_NON_BLOCKING"
    assert "reuse_QUAL_001_002_003_rows" in c["forbidden"]
    assert "balance_on_FUNCTION" in c["forbidden"]
    assert c["historical"]["QUAL_003"]["reuse_forbidden"] is True
    assert c["gates_chosen_before_qual_open"] is True


def test_gates_retention_disposition():
    good = {
        "core_system_macro_f1": 0.35,
        "DOMAIN_macro_f1": 0.35,
        "MEDIATION_macro_f1": 0.34,
        "zero_label_false_positive_rate": 0.08,
        "zero_label_exact_rejection": 0.92,
        "hierarchy_violation_rate": 0.0,
        "mean_predicted_labels_on_zero_gold": 0.12,
    }
    ge = evaluate_core_qual_gates(good)
    assert ge["pass"] is True
    assert ge["FUNCTION_affects_pass_fail"] is False
    assert ge["gates"]["hierarchy_violation"]["pass"] is True

    ret = classify_retention(0.32)
    assert ret["band"] in {
        "STRONG_RETENTION",
        "MODERATE_RETENTION",
        "SEVERE_GENERALIZATION_DROP",
    }
    assert ret["hard_gate"] is False

    bad = dict(good, DOMAIN_macro_f1=0.10, MEDIATION_macro_f1=0.10)
    ge_bad = evaluate_core_qual_gates(bad)
    assert ge_bad["pass"] is False
    assert classify_failure(bad, ge_bad) == "MIXED_CORE_GENERALIZATION_FAILURE"

    d = decide_disposition(preflight_ok=True, execution_ok=True, gate_pass=True)
    assert d["QUALIFICATION_DISPOSITION"] == "V6_CORE_QUALIFICATION_PASS"
    assert d["RELEASE_OUTCOME"] == "V6_CORE_RELEASE_CANDIDATE_APPROVED"
    assert d["NEXT_ACTION"] == "FINALIZE_HYPERLEX_V6_RELEASE_CANDIDATE"
    assert d["HUB_PUBLISH_AUTHORIZED"] is False

    f = decide_disposition(preflight_ok=True, execution_ok=True, gate_pass=False)
    assert f["QUALIFICATION_DISPOSITION"] == "V6_CORE_QUALIFICATION_FAIL"
    assert f["NEXT_ACTION"] == "REVIEW_V6_CORE_QUALIFICATION_FAILURE"

    inv = decide_disposition(preflight_ok=False, execution_ok=False, gate_pass=False)
    assert inv["QUALIFICATION_DISPOSITION"] == "V6_CORE_QUALIFICATION_INVALID"


def test_coverage_sufficient_core_ignores_function():
    assert coverage_sufficient_core(
        {
            "n": 800,
            "stage_a": {"EVIDENCE_PRESENT": 200, "NO_EVIDENCE": 400},
            "cardinality": {"2": 30},
            "zero_label_share": 0.60,
            "active_domain_labels": 8,
            "mediation_supports": {"mediation.internet_register": 20},
        }
    )
    assert not coverage_sufficient_core(
        {
            "n": 100,
            "stage_a": {"EVIDENCE_PRESENT": 10, "NO_EVIDENCE": 10},
            "cardinality": {"2": 1},
            "zero_label_share": 0.10,
            "active_domain_labels": 1,
            "mediation_supports": {"mediation.internet_register": 1},
        }
    )
