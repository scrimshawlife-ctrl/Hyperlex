"""Boundary redefinition tests. No training, no reserve, no BEST writes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY  # noqa: E402
from hyperlexical.classification_v2_boundary_redefinition import (  # noqa: E402
    BEST_SHA,
    HIGH_OVERLAP_COSINE,
    MATERIAL_OVERLAP_REDUCTION,
    PHASE_EXECUTION_SHA,
    PRESERVED_NOISE_COUNTS,
    REDEF_RULE,
    assemble_boundary_redefinition,
    assess_split_candidates,
    build_family_contract,
    build_pairwise_rule,
    classify_training_row,
    count_high_overlap_family_pairs,
    next_engineering_action,
    preserved_noise_classifications,
    redefinition_contract,
    training_gate_result,
)


def test_contract_pins_material_threshold_before_results():
    contract = redefinition_contract()
    assert contract["rule"] == REDEF_RULE
    assert contract["material_overlap_reduction"] == MATERIAL_OVERLAP_REDUCTION == 0.30
    assert contract["high_overlap_cosine"] == HIGH_OVERLAP_COSINE == 0.80
    assert contract["train"] is False
    assert contract["mutates_ontology"] is False
    assert contract["historical_boundaries_mutated"] is False
    assert contract["reserve_scored"] is False
    assert contract["moves_best"] is False
    assert contract["phase_execution_sha256"] == PHASE_EXECUTION_SHA
    assert contract["best_sha256"] == BEST_SHA
    assert PRESERVED_NOISE_COUNTS == {"KEEP": 3, "RELABEL_CANDIDATE": 1, "DROP": 3}


def test_family_contract_and_pairwise_rule_shape():
    contract = build_family_contract(
        "social-status",
        pack={
            "positive_cues": ["status", "prestige"],
            "nearest_competitors": ["approval-disapproval"],
            "exclusion_cues": ["effeminate (approval-disapproval) without social"],
            "shared_overlapping_cues": {"approval-disapproval": ["person"]},
        },
        evidence={"ambiguous_training_rows": [{"second_family": "approval-disapproval"}]},
        texts=["A social status honorific marking prestige hierarchy"],
    )
    assert contract["family"] == "social-status"
    assert "status" in contract["required_semantic_core"] or "prestige" in contract["required_semantic_core"]
    assert "approval-disapproval" in contract["nearest_competitors"]
    other = build_family_contract(
        "approval-disapproval",
        pack={"positive_cues": ["derogatory"], "nearest_competitors": ["social-status"], "exclusion_cues": []},
        evidence={},
        texts=["A derogatory insult used as disapproval"],
    )
    rule = build_pairwise_rule(
        "social-status",
        "approval-disapproval",
        contract_a=contract,
        contract_b=other,
        texts_a=["A social status honorific marking prestige hierarchy"],
        texts_b=["A derogatory insult used as disapproval"],
    )
    assert rule["family_a"] == "social-status"
    assert rule["a_distinguishing_semantics"]
    assert rule["b_distinguishing_semantics"]


def test_row_classifier_preserves_noise_audit_and_flags_collisions():
    contracts = {
        family: build_family_contract(family, pack={}, evidence={}, texts=[f"{family} core example text here"])
        for family in ACTIVE_FAMILY_VOCABULARY
    }
    contracts["social-status"] = build_family_contract(
        "social-status",
        pack={"positive_cues": ["status"], "nearest_competitors": ["approval-disapproval"], "exclusion_cues": []},
        evidence={},
        texts=["prestige status hierarchy elite"],
    )
    contracts["approval-disapproval"] = build_family_contract(
        "approval-disapproval",
        pack={"positive_cues": ["derogatory"], "nearest_competitors": ["social-status"], "exclusion_cues": []},
        evidence={},
        texts=["derogatory insult pejorative disapproval"],
    )
    rules = {
        "approval-disapproval||social-status": build_pairwise_rule(
            "social-status",
            "approval-disapproval",
            contract_a=contracts["social-status"],
            contract_b=contracts["approval-disapproval"],
            texts_a=["prestige status hierarchy elite"],
            texts_b=["derogatory insult pejorative disapproval"],
        )
    }
    dropped = classify_training_row(
        family="music-entertainment",
        text="A type of tuning",
        identity="90544f171008d3cf" + "0" * 48,
        contracts=contracts,
        pairwise_rules=rules,
    )
    assert dropped["decision"] == "DROP"
    keep = classify_training_row(
        family="social-status",
        text="An honorific marking high social status and prestige hierarchy",
        identity="abc123",
        contracts=contracts,
        pairwise_rules=rules,
    )
    assert keep["decision"] == "KEEP"
    relabel = classify_training_row(
        family="social-status",
        text="A derogatory pejorative insult of strong disapproval",
        identity="def456",
        contracts=contracts,
        pairwise_rules=rules,
    )
    assert relabel["decision"] == "RELABEL_CANDIDATE"
    assert relabel["relabel_to"] == "approval-disapproval"


def test_overlap_count_and_gate_use_predeclared_threshold():
    # orthogonal axes => no high overlap
    vectors = {}
    for index, family in enumerate(ACTIVE_FAMILY_VOCABULARY):
        vector = [0.0] * len(ACTIVE_FAMILY_VOCABULARY)
        vector[index] = 1.0
        vectors[family] = [vector, list(vector)]
    pre = count_high_overlap_family_pairs(vectors)
    assert pre["high_overlap_pair_count"] == 0
    # collapse two families onto same axis
    collapsed = {family: list(rows) for family, rows in vectors.items()}
    same = [1.0] + [0.0] * (len(ACTIVE_FAMILY_VOCABULARY) - 1)
    collapsed["social-status"] = [same, same]
    collapsed["approval-disapproval"] = [same, same]
    mid = count_high_overlap_family_pairs(collapsed)
    assert mid["high_overlap_pair_count"] >= 1
    support = {family: 12 for family in ACTIVE_FAMILY_VOCABULARY}
    gate_closed = training_gate_result(pre=mid, post=mid, support_post=support)
    assert gate_closed["training_gate"] == "CLOSED"
    # remove one family vectors to simulate filter resolving the pair
    fixed = {family: list(rows) for family, rows in collapsed.items()}
    axis = [0.0] * len(ACTIVE_FAMILY_VOCABULARY)
    axis[1] = 1.0
    fixed["approval-disapproval"] = [axis, axis]
    post = count_high_overlap_family_pairs(fixed)
    # craft pre with enough pairs that 30% reduction is measurable
    pre_many = {
        "high_overlap_pair_count": 10,
        "collapse_high_overlap_pairs": 8,
        "largest_collapse_component": 10,
        "threshold": HIGH_OVERLAP_COSINE,
    }
    post_few = {
        "high_overlap_pair_count": 6,
        "collapse_high_overlap_pairs": 4,
        "largest_collapse_component": 5,
        "threshold": HIGH_OVERLAP_COSINE,
    }
    gate = training_gate_result(pre=pre_many, post=post_few, support_post=support)
    assert gate["overlap_reduction"] == 0.4
    assert gate["training_gate"] == "OPEN"


def test_preserved_noise_and_split_assessment_helpers():
    presets = preserved_noise_classifications()
    assert len(presets) == 7
    assert sum(1 for row in presets if row["decision"] == "DROP") == 3
    assert sum(1 for row in presets if row["decision"] == "KEEP") == 3
    assert sum(1 for row in presets if row["decision"] == "RELABEL_CANDIDATE") == 1
    assessments = assess_split_candidates(
        [{"family_a": "approval-disapproval", "family_b": "social-status"}],
        pre_pairs=[{"family_a": "approval-disapproval", "family_b": "social-status"}],
        post_pairs=[],
    )
    assert assessments[0]["status"] == "RESOLVED_BY_BOUNDARY_FILTER"
    assert assessments[0]["split_performed"] is False
    closed = next_engineering_action({"training_gate": {"training_gate": "CLOSED"}})
    assert "BOUNDARY_OVERLAP_STILL_BLOCKS_TRAINING" in closed


def test_assemble_requires_nineteen_contracts():
    contracts = {
        family: build_family_contract(family, pack={}, evidence={}, texts=[f"{family} example definition prose"])
        for family in ACTIVE_FAMILY_VOCABULARY
    }
    support = {family: 3 for family in ACTIVE_FAMILY_VOCABULARY}
    for family in ("betting-sharp", "internet-slang", "memetic"):
        support[family] = 12
    pre = {
        "high_overlap_pair_count": 10,
        "collapse_high_overlap_pairs": 8,
        "largest_collapse_component": 13,
        "threshold": 0.8,
        "high_overlap_pairs": [],
    }
    post = {
        "high_overlap_pair_count": 5,
        "collapse_high_overlap_pairs": 3,
        "largest_collapse_component": 6,
        "threshold": 0.8,
        "high_overlap_pairs": [],
    }
    gate = training_gate_result(pre=pre, post=post, support_post=support)
    artifact = assemble_boundary_redefinition(
        {
            "family_contracts": contracts,
            "pairwise_rules": [],
            "row_classifications": [],
            "row_status_counts": {"KEEP": 1},
            "support_post": support,
            "overlap_pre": pre,
            "overlap_post": post,
            "pair_overlap_table": [],
            "split_candidate_assessments": [],
            "training_gate": gate,
        }
    )
    assert artifact["boundary_redefinition_state"] == "SEALED"
    assert len(artifact["family_contracts"]) == 19
    assert artifact["train"] is False
