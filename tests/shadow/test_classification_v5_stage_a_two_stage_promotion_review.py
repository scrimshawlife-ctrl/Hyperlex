"""Unit tests for Stage-A two-stage promotion review helpers."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a_two_stage_promotion_review import (  # noqa: E402
    EXPECTED_GATE1_THRESHOLD,
    EXPECTED_GATE2_PRESENT_THRESHOLD,
    EXPECTED_SELECTED_CHECKPOINT_SHA256,
    KNOWN_LIMITATIONS,
    PROMOTE_ACTION,
    REVIEW_RULE,
    best_semantics_recommendation,
    choose_promotion_decision,
    metric_parity,
    reserve_policy_determination,
    residual_risk_review,
    verify_architecture_identity,
)


def test_frozen_review_constants():
    assert REVIEW_RULE == "REVIEW_V5_STAGE_A_TWO_STAGE_PROMOTION"
    assert PROMOTE_ACTION == "PROMOTE_V5_STAGE_A_TWO_STAGE_SELECTED"
    assert EXPECTED_SELECTED_CHECKPOINT_SHA256.startswith("cd2829c1")
    assert EXPECTED_GATE1_THRESHOLD == 0.75
    assert EXPECTED_GATE2_PRESENT_THRESHOLD == 0.50


def test_metric_parity_and_architecture():
    expected = {"a": 1.0, "b": 0.5}
    assert metric_parity({"a": 1.0, "b": 0.5}, expected)["pass"] is True
    assert metric_parity({"a": 1.0, "b": 0.6}, expected)["pass"] is False
    keys = [
        "encoder.layers.20.weight",
        "encoder.layers.21.weight",
        "gate1_head.weight",
        "gate1_head.bias",
        "gate2_head.weight",
        "gate2_head.bias",
    ]
    # Not 48 encoder tensors → fail count check.
    bad = verify_architecture_identity(keys)
    assert bad["pass"] is False
    keys48 = [f"encoder.t{i}" for i in range(48)] + [
        "gate1_head.weight",
        "gate1_head.bias",
        "gate2_head.weight",
        "gate2_head.bias",
    ]
    good = verify_architecture_identity(keys48)
    assert good["pass"] is True
    assert good["flat_3way_canonical"] is False


def test_decision_and_policies():
    ready = choose_promotion_decision(
        integrity_pass=True, replay_pass=True, architecture_pass=True
    )
    assert ready["PROMOTION_DECISION"] == "PROMOTION_READY"
    assert ready["NEXT_ACTION"] == PROMOTE_ACTION
    assert ready["promote"] is False
    blocked = choose_promotion_decision(
        integrity_pass=True, replay_pass=False, architecture_pass=True
    )
    assert blocked["PROMOTION_DECISION"] == "PROMOTION_BLOCKED"
    invalid = choose_promotion_decision(
        integrity_pass=False, replay_pass=True, architecture_pass=True
    )
    assert invalid["PROMOTION_DECISION"] == "PROMOTION_REVIEW_INVALID"
    best = best_semantics_recommendation()
    assert best["recommendation"] == "STAGE_A_BEST"
    assert best["overwrite_model_wide_BEST"] is False
    reserve = reserve_policy_determination()
    assert reserve["fresh_reserve_required_for_internal_canonical_adoption"] is False
    assert reserve["reserve_scored_in_review"] is False
    risks = residual_risk_review()
    assert len(risks["known_limitations"]) == 4
    assert all(item["status"] == "KNOWN_LIMITATION" for item in KNOWN_LIMITATIONS)
