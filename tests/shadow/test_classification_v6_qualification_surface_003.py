"""CPU tests for V6 QUAL-003 surface contracts."""

from __future__ import annotations

from hyperlexical.classification_v6_operating_pipeline_harden import (
    OPERATING_QUALIFICATION_GATES,
)
from hyperlexical.classification_v6_qualification_surface_003 import (
    OPERATING_PACKAGE_SHA256,
    PHASE_RULE,
    QUALIFICATION_ID,
    TARGET_N_MIN,
    coverage_sufficient_operating,
    decide_surface_state,
    gate_binding,
    qual_003_contract,
)


def test_qual_003_binds_operating_gates_and_spent_002():
    c = qual_003_contract()
    assert c["PHASE_RULE"] == PHASE_RULE
    assert c["QUALIFICATION_ID"] == QUALIFICATION_ID
    assert c["historical"]["QUAL_002"]["status"] == "EVALUATION_SPENT"
    assert c["historical"]["QUAL_002"]["reuse_forbidden"] is True
    g = gate_binding()
    assert g["gates"]["system_macro_f1_min"] == OPERATING_QUALIFICATION_GATES[
        "system_macro_f1_min"
    ]
    assert g["gates"]["zero_label_false_positive_rate_max"] == 0.35
    assert g["operating_package_sha256"] == OPERATING_PACKAGE_SHA256
    assert c["MODEL_WIDE_BEST_MUTATED"] is False
    assert "score_QUAL_003" in c["forbidden"]


def test_decide_sealed_and_coverage_operating():
    d = decide_surface_state(
        ontology_compatible=True,
        gold_stable=True,
        identifiability_pass=True,
        disjointness_pass=True,
        coverage_sufficient=True,
        seal_complete=True,
        model_executions=0,
        n_rows=TARGET_N_MIN,
    )
    assert d["SURFACE_STATE"] == "V6_QUALIFICATION_003_SURFACE_SEALED"
    assert d["NEXT_ACTION"] == "EXECUTE_V6_QUALIFICATION_003_ONCE"
    ok = coverage_sufficient_operating(
        {
            "n": 900,
            "stage_a": {"EVIDENCE_PRESENT": 300, "NO_EVIDENCE": 500},
            "cardinality": {"0": 500, "1": 300, "2": 80, "3+": 20},
            "zero_label_share": 0.55,
            "active_domain_labels": 8,
            "active_function_labels": 3,
            "mediation_supports": {"mediation.internet_register": 40},
        }
    )
    assert ok is True
    thin = coverage_sufficient_operating(
        {
            "n": 900,
            "stage_a": {"EVIDENCE_PRESENT": 800, "NO_EVIDENCE": 40},
            "cardinality": {"0": 40, "1": 800, "2": 40, "3+": 20},
            "zero_label_share": 0.05,
            "active_domain_labels": 8,
            "active_function_labels": 3,
            "mediation_supports": {"mediation.internet_register": 40},
        }
    )
    assert thin is False


def test_gold_unstable_reviews():
    d = decide_surface_state(
        ontology_compatible=True,
        gold_stable=False,
        identifiability_pass=True,
        disjointness_pass=True,
        coverage_sufficient=True,
        seal_complete=False,
        model_executions=0,
        n_rows=900,
    )
    assert d["NEXT_ACTION"] == "REVIEW_V6_QUALIFICATION_003_GOLD"
