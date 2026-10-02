"""CPU tests for V6 semantic-pipeline hardening contracts."""

from __future__ import annotations

from hyperlexical.classification_v6_human_ontology_settlement import FINAL_ONTOLOGY_ID
from hyperlexical.classification_v6_semantic_pipeline_harden import (
    BAKEOFF_THRESHOLDS,
    PIPELINE_CANDIDATE_ID,
    QUALIFICATION_GATES,
    SELECTED_ENCODER_MODEL_ID,
    SELECTED_ENCODER_REVISION,
    WITNESS_DEV_MACRO,
    WITNESS_REP_MACRO,
    classify_reproduction,
    classify_source_robustness,
    decide_readiness,
    harden_contract,
    hierarchy_constraints_payload,
    pipeline_candidate_contract,
    qual_metadata_compatibility,
    qualification_preregistration,
    runtime_forward_schema,
    threshold_manifest_payload,
)


def test_pipeline_contract_pins_encoder_and_heads():
    c = harden_contract()
    assert c["PHASE_RULE"].startswith("HARDEN_V6")
    assert c["pipeline_candidate"]["PIPELINE_CANDIDATE_ID"] == PIPELINE_CANDIDATE_ID
    enc = c["pipeline_candidate"]["encoder"]
    assert enc["model_id"] == SELECTED_ENCODER_MODEL_ID
    assert enc["revision"] == SELECTED_ENCODER_REVISION
    assert enc["trainable_parameters_required"] == 0
    assert enc["floating_upstream_revision_forbidden"] is True
    heads = c["pipeline_candidate"]["heads"]
    assert heads["axes"]["domain"]["output_dimension"] == 11
    assert heads["axes"]["function"]["output_dimension"] == 4
    assert heads["axes"]["mediation"]["output_dimension"] == 1
    assert heads["axes"]["domain"]["dropout"] == 0.0
    assert heads["shared_topology"]["activation"] == "ReLU"
    assert "inspect_QUAL_rows" in c["forbidden"]
    assert c["pointer_policy"]["MODEL_WIDE_BEST"] == "UNCHANGED"
    assert c["historical_control"]["do_not_mutate"] is True


def test_ontology_and_constraint_hashes_stable():
    cand = pipeline_candidate_contract()
    assert cand["ontology"]["ontology_version"] == FINAL_ONTOLOGY_ID
    assert cand["ontology"]["structure"] == "HIERARCHICAL_MULTI_LABEL"
    assert len(cand["ontology"]["label_schema_hash"]) == 64
    assert len(cand["ontology"]["hierarchy_hash"]) == 64
    cons = hierarchy_constraints_payload()
    assert cons["CONSTRAINT_MANIFEST_ID"] == "HYPERLEX_V6_HIERARCHY_CONSTRAINTS_V1"
    assert cons["rules"][0]["child"].endswith("ai_discourse")
    assert cons["rules"][0]["parent"].endswith("technology")
    th = threshold_manifest_payload()
    assert th["status"] == "FROZEN"
    assert th["selection_surface"] == "DEV_ONLY"
    assert th["thresholds_ordered"] == BAKEOFF_THRESHOLDS
    assert len(th["thresholds"]["domain"]) == 11


def test_qualification_gates_use_retention_floor():
    q = qualification_preregistration()
    assert q["gates"]["system_macro_f1_min"] == 0.30
    assert q["gates"]["hierarchy_violation_max"] == 0.05
    assert q["gates"]["no_complete_axis_collapse"] is True
    assert q["gates"]["chosen_before_qual_open"] is True
    assert QUALIFICATION_GATES["legacy_floor_system_macro_f1_min"] == 0.20
    assert "DOMAIN_FP" in q["error_taxonomy"]
    assert "system_macro_f1" in q["metrics"]
    schema = runtime_forward_schema()
    assert "final_domain_labels" in schema["required_fields"]
    assert "hierarchy_adjustments" in schema["required_fields"]


def test_reproduction_and_source_classifiers():
    assert (
        classify_reproduction(
            dev_macro=WITNESS_DEV_MACRO,
            rep_macro=WITNESS_REP_MACRO,
            post_hier=0.0,
            raw_pred_mismatch=0,
            constrained_pred_mismatch=0,
            score_max_abs_delta=0.0,
        )
        == "EXACT_REPRODUCTION"
    )
    assert (
        classify_reproduction(
            dev_macro=WITNESS_DEV_MACRO + 0.01,
            rep_macro=WITNESS_REP_MACRO - 0.01,
            post_hier=0.0,
            raw_pred_mismatch=0,
            constrained_pred_mismatch=0,
        )
        == "SCIENTIFICALLY_EQUIVALENT_REPRODUCTION"
    )
    assert (
        classify_reproduction(
            dev_macro=0.20,
            rep_macro=0.20,
            post_hier=0.0,
            raw_pred_mismatch=0,
            constrained_pred_mismatch=0,
        )
        == "REPRODUCTION_DIVERGED"
    )
    assert (
        classify_source_robustness(
            {"a": 0.44, "b": 0.42, "c": 0.43}, system_macro=0.443
        )
        == "SOURCE_STABLE"
    )
    assert (
        classify_source_robustness(
            {"a": 0.50, "b": 0.05, "c": 0.10}, system_macro=0.443
        )
        == "SOURCE_DEPENDENT"
    )


def test_qual_metadata_legacy_families_require_new_qual():
    meta = {
        "QUALIFICATION_HOLD_ID": "HYPERLEX_V6_QUALIFICATION_001",
        "summary": {"family_counts": {"ai-native": 15, "gaming-meta": 11}, "n": 486},
    }
    out = qual_metadata_compatibility(meta)
    assert out["status"] == "NEW_QUAL_REQUIRED"
    assert out["compatible"] is False
    assert out["rows_inspected"] is False


def test_readiness_hardened_but_qual_surface_blocked():
    d = decide_readiness(
        package_ok=True,
        reproduction_class="SCIENTIFICALLY_EQUIVALENT_REPRODUCTION",
        cold_load_ok=True,
        round_trip_ok=True,
        encoder_immutable=True,
        ontology_hashes_ok=True,
        qual_compat_status="NEW_QUAL_REQUIRED",
        rep_regressed=False,
    )
    assert d["HARDENING_STATE"] == "V6_SEMANTIC_PIPELINE_HARDENED"
    assert d["QUALIFICATION_READINESS"] == "V6_QUALIFICATION_BLOCKED_QUAL_SURFACE"
    assert d["NEXT_ACTION"] == "BUILD_AND_SEAL_FRESH_V6_QUALIFICATION_SURFACE"


def test_readiness_ready_when_qual_compatible():
    d = decide_readiness(
        package_ok=True,
        reproduction_class="NUMERICALLY_EQUIVALENT_REPRODUCTION",
        cold_load_ok=True,
        round_trip_ok=True,
        encoder_immutable=True,
        ontology_hashes_ok=True,
        qual_compat_status="QUAL_SURFACE_COMPATIBLE",
        rep_regressed=False,
    )
    assert d["QUALIFICATION_READINESS"] == "V6_QUALIFICATION_READY"
    assert d["NEXT_ACTION"] == "EXECUTE_V6_FRESH_QUALIFICATION_ONCE"


def test_readiness_blocked_on_divergence():
    d = decide_readiness(
        package_ok=False,
        reproduction_class="REPRODUCTION_DIVERGED",
        cold_load_ok=True,
        round_trip_ok=True,
        encoder_immutable=True,
        ontology_hashes_ok=True,
        qual_compat_status="NEW_QUAL_REQUIRED",
        rep_regressed=True,
    )
    assert d["HARDENING_STATE"] == "V6_SEMANTIC_PIPELINE_HARDEN_FAILED"
    assert d["NEXT_ACTION"] == "REVIEW_V6_REPRESENTATION_HARDENING_FAILURE"
