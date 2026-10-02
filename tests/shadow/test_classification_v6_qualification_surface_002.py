"""CPU tests for V6 QUAL-002 surface contracts."""

from __future__ import annotations

from hyperlexical.classification_v6_human_ontology_settlement import FINAL_ONTOLOGY_ID
from hyperlexical.classification_v6_qualification_surface_002 import (
    HISTORICAL_QUAL_STATUS,
    PRIOR_MEAN_SET_JACCARD,
    QUALIFICATION_ID,
    TARGET_N_MIN,
    classify_agreement_stability,
    decide_surface_state,
    gate_binding,
    ontology_binding,
    qual_002_contract,
)


def test_qual_002_identity_and_historical():
    c = qual_002_contract()
    assert c["QUALIFICATION_ID"] == QUALIFICATION_ID == "HYPERLEX_V6_QUALIFICATION_002"
    assert HISTORICAL_QUAL_STATUS["status"] == "HISTORICAL_SEALED_UNINSPECTED"
    assert HISTORICAL_QUAL_STATUS["ontology_status"] == "ONTOLOGY_INCOMPATIBLE_FOR_FINAL_V6"
    assert HISTORICAL_QUAL_STATUS["unsealed"] is False
    assert "inspect_historical_QUAL_001_rows" in c["forbidden"]
    assert "score_QUAL_with_V6_candidate" in c["forbidden"]
    assert c["pointer_policy"]["MODEL_WIDE_BEST"] == "UNCHANGED"
    assert c["pointer_policy"]["V6_REPRESENTATION_CANDIDATE"] == "UNCHANGED"


def test_ontology_binding_pinned():
    b = ontology_binding()
    assert b["ontology_version"] == FINAL_ONTOLOGY_ID
    assert b["pinned_before_acquisition"] is True
    assert len(b["ontology_hash"]) == 64
    assert len(b["label_schema_hash"]) == 64
    assert len(b["hierarchy_hash"]) == 64
    assert len(b["input_contract_hash"]) == 64
    assert len(b["ontology_binding_sha256"]) == 64


def test_gates_unmodified_from_harden():
    g = gate_binding()
    assert g["gates"]["system_macro_f1_min"] == 0.30
    assert g["gates"]["hierarchy_violation_max"] == 0.05
    assert g["gates"]["no_complete_axis_collapse"] is True
    assert g["modified_in_this_phase"] is False
    assert g["axis_collapse"]["derived_after_qual"] is False
    assert g["retention_analysis_preregistration"]["hard_gate"] is False


def test_agreement_and_surface_decisions():
    assert abs(PRIOR_MEAN_SET_JACCARD - 0.969) < 1e-9
    assert classify_agreement_stability(0.90) == "QUALIFICATION_GOLD_STABLE"
    assert classify_agreement_stability(0.50) == "QUALIFICATION_GOLD_UNSTABLE"
    sealed = decide_surface_state(
        ontology_compatible=True,
        gold_stable=True,
        identifiability_pass=True,
        disjointness_pass=True,
        coverage_sufficient=True,
        seal_complete=True,
        model_executions=0,
        n_rows=TARGET_N_MIN,
    )
    assert sealed["SURFACE_STATE"] == "V6_FRESH_QUALIFICATION_SURFACE_SEALED"
    assert sealed["NEXT_ACTION"] == "EXECUTE_V6_FRESH_QUALIFICATION_ONCE"
    unstable = decide_surface_state(
        ontology_compatible=True,
        gold_stable=False,
        identifiability_pass=True,
        disjointness_pass=True,
        coverage_sufficient=True,
        seal_complete=False,
        model_executions=0,
        n_rows=800,
    )
    assert unstable["NEXT_ACTION"] == "REVIEW_V6_QUALIFICATION_GOLD_INSTABILITY"
    partial = decide_surface_state(
        ontology_compatible=True,
        gold_stable=True,
        identifiability_pass=True,
        disjointness_pass=True,
        coverage_sufficient=False,
        seal_complete=False,
        model_executions=0,
        n_rows=400,
    )
    assert partial["SURFACE_STATE"] == "V6_FRESH_QUALIFICATION_SURFACE_PARTIAL"
    assert partial["NEXT_ACTION"] == "CONTINUE_V6_FRESH_QUALIFICATION_ACQUISITION"
    scored = decide_surface_state(
        ontology_compatible=True,
        gold_stable=True,
        identifiability_pass=True,
        disjointness_pass=True,
        coverage_sufficient=True,
        seal_complete=True,
        model_executions=1,
        n_rows=800,
    )
    assert scored["SURFACE_STATE"] == "V6_FRESH_QUALIFICATION_SURFACE_INVALID"
