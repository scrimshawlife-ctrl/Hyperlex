"""Unit tests for Stage-A-004 architecture/objective investigation helpers."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a_architecture_investigate import (  # noqa: E402
    INVESTIGATE_RULE,
    PRIMARY_DECISIONS,
    architecture_alternative_cards,
    choose_primary_decision,
    classify_bottleneck,
    classify_present_fn_mode,
    classify_separability,
    cosine,
    decompose_fn_modes,
    smallest_reversible_redesign,
)


def test_frozen_rule_and_alternatives():
    assert INVESTIGATE_RULE == "ARCHITECTURE_OR_OBJECTIVE_INVESTIGATION"
    cards = architecture_alternative_cards()
    assert {c["id"] for c in cards} == {
        "A_MULTITASK_PRESENT_DETECTOR",
        "B_TWO_STAGE",
        "C_CURRENT_3CLASS",
    }
    assert len(PRIMARY_DECISIONS) == 5


def test_cosine_and_separability():
    assert cosine([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert (
        classify_separability(
            present_none_centroid_cosine=0.95,
            present_uncertain_centroid_cosine=0.90,
            present_fn_nearest_none_frac=0.70,
            present_fn_nearest_present_frac=0.20,
        )
        == "COLLAPSED"
    )
    assert (
        classify_separability(
            present_none_centroid_cosine=0.60,
            present_uncertain_centroid_cosine=0.70,
            present_fn_nearest_none_frac=0.20,
            present_fn_nearest_present_frac=0.70,
        )
        == "SEPARABLE"
    )


def test_fn_mode_and_decompose():
    assert (
        classify_present_fn_mode(
            {
                "decision": "NO_EVIDENCE",
                "P_EVIDENCE_PRESENT": 0.01,
                "P_NO_EVIDENCE": 0.98,
                "P_UNCERTAIN": 0.01,
                "nearest_centroid": "NO_EVIDENCE",
            }
        )
        == "REPRESENTATION_FAILURE"
    )
    assert (
        classify_present_fn_mode(
            {
                "decision": "UNCERTAIN",
                "P_EVIDENCE_PRESENT": 0.52,
                "P_NO_EVIDENCE": 0.20,
                "P_UNCERTAIN": 0.28,
                "nearest_centroid": "EVIDENCE_PRESENT",
            }
        )
        == "THRESHOLD_FAILURE"
    )
    rows = [
        {
            "decision": "NO_EVIDENCE",
            "P_EVIDENCE_PRESENT": 0.01,
            "P_NO_EVIDENCE": 0.98,
            "P_UNCERTAIN": 0.01,
            "nearest_centroid": "NO_EVIDENCE",
        },
        {
            "decision": "UNCERTAIN",
            "P_EVIDENCE_PRESENT": 0.40,
            "P_NO_EVIDENCE": 0.20,
            "P_UNCERTAIN": 0.40,
            "nearest_centroid": "EVIDENCE_PRESENT",
        },
    ]
    decomp = decompose_fn_modes(rows)
    assert decomp["n"] == 2
    assert decomp["counts"]["REPRESENTATION_FAILURE"] == 1
    assert decomp["counts"]["PRESENT_TO_UNCERTAIN"] == 1


def test_primary_decision_forces_redesign_after_focal_falsified():
    bottleneck = classify_bottleneck(
        separability="PARTIALLY_SEPARABLE",
        present_fn_profile="CONFIDENT_NONE",
        uncertain_decision_ignore_frac=0.70,
        focal_already_falsified=True,
    )
    assert bottleneck in {"MIXED", "OBJECTIVE_LIMITED"}
    decision = choose_primary_decision(
        bottleneck=bottleneck,
        separability="PARTIALLY_SEPARABLE",
        present_fn_profile="CONFIDENT_NONE",
        focal_already_falsified=True,
        uncertain_policy_invisible=True,
        dataset_change_justified=False,
    )
    assert decision["PRIMARY_DECISION"] == "STAGE_A_ARCHITECTURE_REDESIGN_REQUIRED"
    assert decision["architecture_change_required"] is True
    assert decision["dataset_change_required"] is False
    assert decision["new_experiment_required"] is False
    assert decision["NEXT_ACTION"] == "DESIGN_V5_STAGE_A_ARCHITECTURE_REDESIGN_SPEC"
    redesign = smallest_reversible_redesign(
        primary=decision["PRIMARY_DECISION"],
        bottleneck=bottleneck,
        uncertain_policy_invisible=True,
        separability="PARTIALLY_SEPARABLE",
    )
    assert redesign["train_authorized"] is False
    assert redesign["change_id"].startswith("B_")
