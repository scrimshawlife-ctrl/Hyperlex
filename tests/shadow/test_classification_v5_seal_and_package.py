"""Tests for V1R2 Stage-A/B pipeline seal + packaging contracts."""

from __future__ import annotations

from hyperlexical.classification_v5_seal_and_package import (
    PACKAGING_ID,
    SEAL_RULE,
    V5_STAGE_A_B_PIPELINE_STATE,
    V5_STAGE_B_STATE,
    build_runtime_forward,
    compose_runtime_row,
    package_contract,
    pipeline_dependency_manifest,
    validate_integration_metrics,
    validate_round_trip,
)
from hyperlexical.classification_v5_stage_a_b_pipeline import (
    PIPELINE_ID,
    runtime_registry,
    verify_entry_gating,
    verify_stage_b_parent_and_floors,
)
from hyperlexical.classification_v5_stage_a_canonical import STAGE_A_BEST_SHA256
from hyperlexical.classification_v5_stage_b import FROZEN_INDEX_SHA256


def test_pipeline_pins_and_registry():
    assert PIPELINE_ID == "HYPERLEX_V5_STAGE_A_B_PIPELINE_V1"
    assert SEAL_RULE.startswith("SEAL_AND_PACKAGE_")
    assert V5_STAGE_B_STATE == "CANONICAL_FOR_V1R2_PIPELINE"
    assert V5_STAGE_A_B_PIPELINE_STATE == "CANONICAL_FROZEN"
    assert verify_entry_gating()["pass"] is True
    assert verify_stage_b_parent_and_floors()["pass"] is True
    reg = runtime_registry()
    assert reg["STAGE_A_BEST"] == STAGE_A_BEST_SHA256
    assert reg["STAGE_B_INDEX"] == FROZEN_INDEX_SHA256
    assert reg["V5_PIPELINE"] == PIPELINE_ID
    assert reg["merged_into_model_wide_best"] is False


def test_manifest_and_package_contract():
    manifest = pipeline_dependency_manifest(code_revision="deadbeef")
    assert manifest["pipeline_version"] == PIPELINE_ID
    assert manifest["stage_b_index_sha256"].startswith("4febe96e")
    assert manifest["stage_b_score_floor"] == 0.83
    assert manifest["stage_a_thresholds"]["relation"] == 0.60
    assert "PIPELINE_DEPENDENCY_MANIFEST_SHA256" in manifest
    contract = package_contract(code_revision="deadbeef")
    assert contract["PACKAGING_ID"] == PACKAGING_ID
    assert contract["publish_authorized"] is False
    assert contract["PIPELINE_DEPENDENCY_MANIFEST_SHA256"] == (
        manifest["PIPELINE_DEPENDENCY_MANIFEST_SHA256"]
    )
    assert contract["historical_state"]["historical_v1r9_stage_b_index"][
        "status"
    ] == "HISTORICAL"


def test_runtime_forward_nulls_when_stage_b_skipped():
    none = compose_runtime_row(
        stage_a_decision="NO_EVIDENCE",
        p_relation=0.1,
        p_resolvable=0.9,
        ranked_candidates=[{"family": "memetic", "score": 0.99}],
    )
    assert none["stage_b_executed"] is False
    assert none["final_decision"] == "NO_EVIDENCE"
    assert none["family_score"] is None
    assert none["predicted_family"] is None
    uncertain = compose_runtime_row(
        stage_a_decision="UNCERTAIN",
        p_relation=0.9,
        p_resolvable=0.2,
        ranked_candidates=[{"family": "memetic", "score": 0.99}],
    )
    assert uncertain["stage_b_executed"] is False
    assert uncertain["final_decision"] == "ABSTAIN"
    family = compose_runtime_row(
        stage_a_decision="EVIDENCE_PRESENT",
        p_relation=0.9,
        p_resolvable=0.9,
        ranked_candidates=[
            {"family": "memetic", "score": 0.95},
            {"family": "gaming-meta", "score": 0.05},
        ],
    )
    assert family["stage_b_executed"] is True
    assert family["final_decision"] == "FAMILY"
    assert family["predicted_family"] == "memetic"
    assert family["family_score"] == 0.95
    assert family["runner_up_family"] == "gaming-meta"


def test_integration_and_round_trip_validators():
    ok = validate_integration_metrics(
        {
            "false_evidence_entry_rate_on_none": 0.03357,
            "family_emission_precision": 0.809,
            "selective_accuracy": 0.936,
            "primary_gate_pass": True,
            "secondary_gate_pass": True,
            "gating": {
                "none_entered_stage_b": 0,
                "uncertain_entered_stage_b": 0,
                "pass": True,
            },
        }
    )
    assert ok["pass"] is True
    bad = validate_integration_metrics(
        {
            "false_evidence_entry_rate_on_none": 0.20,
            "family_emission_precision": 0.809,
            "selective_accuracy": 0.936,
            "primary_gate_pass": False,
            "secondary_gate_pass": True,
            "gating": {
                "none_entered_stage_b": 0,
                "uncertain_entered_stage_b": 0,
                "pass": True,
            },
        }
    )
    assert bad["pass"] is False
    rt = validate_round_trip(
        {
            "stage_a_decision_mismatch_count": 0,
            "stage_b_execution_mismatch_count": 0,
            "family_final_decision_mismatch_count": 0,
        }
    )
    assert rt["pass"] is True
    # build_runtime_forward sanity for executed ambiguous path
    amb = build_runtime_forward(
        stage_a_decision="EVIDENCE_PRESENT",
        p_relation=0.9,
        p_resolvable=0.9,
        stage_b_result={"decision_type": "AMBIGUOUS", "family": None},
        stage_b_executed=True,
    )
    assert amb["final_decision"] == "AMBIGUOUS"
    assert amb["family_score"] is None
