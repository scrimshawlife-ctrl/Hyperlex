"""CPU tests for V6 representation-rebase contracts."""

from __future__ import annotations

from hyperlexical.classification_v6_representation_rebase import (
    ADVANCEMENT,
    MPNET_WITNESS,
    classify_geometry,
    classify_label_strength,
    eligible_candidate,
    label_texts,
    rebase_contract,
    select_rebase_state,
)


def test_contract_locks_floors_and_witness():
    c = rebase_contract()
    assert c["mpnet_witness"]["ZERO_SHOT_REP_SYSTEM_MACRO_F1"] == MPNET_WITNESS[
        "ZERO_SHOT_REP_SYSTEM_MACRO_F1"
    ]
    assert abs(c["mpnet_witness"]["ZERO_SHOT_REP_SYSTEM_MACRO_F1"] - 0.20555757451039375) < 1e-12
    assert c["advancement"]["min_rep_system_macro_f1"] == 0.20
    assert c["advancement"]["floors_locked"] is True
    assert c["historical_control"]["do_not_mutate"] is True
    assert "mutate_MODEL_WIDE_BEST" in c["forbidden"]
    assert c["qual_policy"]["inspected"] is False
    texts = label_texts("short_definition")
    full = label_texts("full_boundary_contract")
    assert "domain.gambling" in texts
    assert "NEAR_NEIGHBORS" in full["domain.technology.ai_discourse"]


def test_label_strength_and_geometry():
    assert classify_label_strength(0.01, 20) == "DEAD_LABEL"
    assert classify_label_strength(0.40, 20) == "STRONG_LABEL"
    assert classify_label_strength(0.50, 3) == "LOW_SUPPORT"
    assert classify_geometry(
        cosine_drift=0.99, nn_retention=0.95, margin_delta=0.0, rep_delta=0.0
    ) == "SEMANTIC_GEOMETRY_PRESERVED"
    assert classify_geometry(
        cosine_drift=0.80, nn_retention=0.50, margin_delta=-0.05, rep_delta=-0.02
    ) == "SEMANTIC_GEOMETRY_DEGRADED"


def test_select_states():
    zs = {
        "id": "zs_mpnet",
        "formulation": "zero_shot_similarity",
        "rep_system_macro_f1": 0.206,
        "dev_macro_f1": 0.21,
        "hierarchy_violation_rate_rep": 0.0,
        "axis_collapse": False,
        "geometry": "SEMANTIC_GEOMETRY_PRESERVED",
    }
    trained_weak = {
        "id": "trained_201",
        "formulation": "frozen_linear",
        "rep_system_macro_f1": 0.201,
        "dev_macro_f1": 0.22,
        "hierarchy_violation_rate_rep": 0.0,
        "axis_collapse": False,
    }
    trained_win = {
        "id": "trained_22",
        "formulation": "frozen_linear",
        "rep_system_macro_f1": 0.22,
        "dev_macro_f1": 0.23,
        "hierarchy_violation_rate_rep": 0.0,
        "axis_collapse": False,
    }
    assert eligible_candidate(zs) is True
    s0 = select_rebase_state([zs, trained_weak])
    assert s0["REBASE_STATE"] == "V6_REPRESENTATION_REBASE_ZERO_SHOT_ONLY"
    assert s0["NEXT_ACTION"] == "HARDEN_V6_ZERO_SHOT_SEMANTIC_MATCHING_PIPELINE"
    assert s0["REPRESENTATION_IMPROVEMENT"] is False
    s1 = select_rebase_state([zs, trained_win])
    assert s1["REBASE_STATE"] == "V6_REPRESENTATION_REBASE_ADVANCE"
    assert s1["selected"] == "trained_22"
    assert ADVANCEMENT["trained_improvement_bar"] > 0.20
    s2 = select_rebase_state(
        [
            {
                "id": "fail",
                "formulation": "zero_shot_similarity",
                "rep_system_macro_f1": 0.11,
                "dev_macro_f1": 0.12,
                "hierarchy_violation_rate_rep": 0.0,
                "axis_collapse": False,
            }
        ]
    )
    assert s2["REBASE_STATE"] == "V6_REPRESENTATION_REBASE_NO_ADVANCE"
