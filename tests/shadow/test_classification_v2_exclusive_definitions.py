"""Exclusive-definition pass tests. No training, no reserve, no BEST writes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY  # noqa: E402
from hyperlexical.classification_v2_exclusive_definitions import (  # noqa: E402
    BEST_SHA,
    BOUNDARY_REDEFINITION_SHA,
    EXCLUSIVE_RULE,
    HIGH_OVERLAP_COSINE,
    MATERIAL_OVERLAP_REDUCTION,
    assemble_exclusive_pass,
    exclusive_admission_ok,
    exclusive_contract,
    select_collision_replacements,
)


def test_exclusive_contract_pins_and_forbids_train():
    contract = exclusive_contract()
    assert contract["rule"] == EXCLUSIVE_RULE
    assert contract["train"] is False
    assert contract["moves_best"] is False
    assert contract["reserve_scored"] is False
    assert contract["historical_boundaries_mutated"] is False
    assert contract["mutates_ontology"] is False
    assert contract["material_overlap_reduction"] == MATERIAL_OVERLAP_REDUCTION == 0.30
    assert contract["high_overlap_cosine"] == HIGH_OVERLAP_COSINE == 0.80
    assert contract["best_sha256"] == BEST_SHA
    assert contract["boundary_redefinition_sha256"] == BOUNDARY_REDEFINITION_SHA


def test_select_prefers_sacrificial_and_protects_sparse():
    support = {family: 20 for family in ACTIVE_FAMILY_VOCABULARY}
    support["internet-slang"] = 12
    support["ai-native"] = 100
    collisions = [
        {
            "cosine": 0.95,
            "family_a": "ai-native",
            "family_b": "internet-slang",
            "identity_a": "aaa",
            "identity_b": "bbb",
            "core_hits_a": 0,
            "core_hits_b": 0,
            "text_a": "agent prompt",
            "text_b": "online slang",
        }
    ]
    decisions = select_collision_replacements(collisions, support=support)
    assert len(decisions) == 1
    assert decisions[0]["identity"] == "aaa"
    assert decisions[0]["family"] == "ai-native"
    # sparse at floor: cannot drop internet-slang
    support["ai-native"] = 12
    support["internet-slang"] = 12
    collisions = [
        {
            "cosine": 0.91,
            "family_a": "internet-slang",
            "family_b": "social-status",
            "identity_a": "isl",
            "identity_b": "soc",
            "core_hits_a": 0,
            "core_hits_b": 1,
            "text_a": "chat fragment",
            "text_b": "status rank",
        }
    ]
    decisions = select_collision_replacements(collisions, support=support)
    assert decisions[0]["identity"] == "soc"


def test_exclusive_admission_blocks_competitor_dominant_cores():
    assert exclusive_admission_ok(
        family="social-status",
        text="A marker of high social status and prestige rank",
        competitor_families=["approval-disapproval", "relationship-dating"],
    )
    assert not exclusive_admission_ok(
        family="social-status",
        text="A derogatory insult of strong disapproval pejorative",
        competitor_families=["approval-disapproval"],
    )
    # Unique honorific sense without core lexemes still ok if competitors are weak.
    assert exclusive_admission_ok(
        family="social-status",
        text="A title of respect used when addressing an elder",
        competitor_families=["approval-disapproval"],
    )


def test_assemble_exclusive_pass_shape():
    support = {family: 12 for family in ACTIVE_FAMILY_VOCABULARY}
    redef = {
        "artifact_sha256": "x" * 64,
        "training_gate": {"training_gate": "CLOSED", "overlap_reduction": 0.1},
        "overlap_pre": {"high_overlap_pair_count": 10},
        "overlap_post": {"high_overlap_pair_count": 9},
        "overlap_reduction": 0.1,
        "row_status_counts": {"KEEP": 1},
        "split_candidate_assessments": [],
    }
    artifact = assemble_exclusive_pass(
        {
            "replacement_decisions": [
                {
                    "decision": "DROP",
                    "family": "ai-native",
                    "identity": "abc",
                    "reason": "sacrificial_large_family",
                    "peer_family": "internet-slang",
                    "cosine": 0.9,
                    "text": "x",
                }
            ],
            "acquired_rows": [],
            "support_pre": support,
            "support_post_overlay": support,
            "collision_pairs_pre": 5,
            "overlay_sha256": "y" * 64,
            "boundary_redefinition": redef,
        }
    )
    assert artifact["exclusive_state"] == "SEALED"
    assert artifact["train"] is False
    assert "EXCLUSIVE_DEFINITIONS" in artifact["next_engineering_action"]
