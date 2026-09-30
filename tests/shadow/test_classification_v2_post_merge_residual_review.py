"""Post-merge residual review tests. No train / reserve / BEST / ontology mutation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v2_ontology_merge_pair import (  # noqa: E402
    KEEP_FAMILY,
    MERGED_LABEL,
)
from hyperlexical.classification_v2_post_merge_residual_review import (  # noqa: E402
    MERGE_PAIR_ARTIFACT_SHA,
    REVIEW_RULE,
    analyze_se_rd,
    assemble_residual_review,
    decide_residual_recommendation,
    degree_table,
    residual_review_contract,
)


def test_contract_forbids_mutation_and_train():
    contract = residual_review_contract()
    assert contract["rule"] == REVIEW_RULE
    assert contract["train"] is False
    assert contract["moves_best"] is False
    assert contract["reserve_scored"] is False
    assert contract["applies_ontology_change"] is False
    assert contract["opens_training_gate"] is False
    assert contract["merges_relationship_dating_automatically"] is False
    assert contract["merge_pair_artifact_sha256"] == MERGE_PAIR_ARTIFACT_SHA
    assert contract["jev"] == "OFF"


def test_decide_keep_se_rd_when_lexically_distinct():
    se_rd = {
        "cosine": 0.93,
        "lexically_distinct": True,
        "shared_token_ratio": 0.0,
        "above_overlap_threshold": True,
    }
    degrees = [
        {"family": "internet-slang", "degree": 8},
        {"family": "spiritual-mystic", "degree": 8},
        {"family": MERGED_LABEL, "degree": 7},
        {"family": KEEP_FAMILY, "degree": 6},
    ]
    decision = decide_residual_recommendation(
        se_rd=se_rd,
        degrees=degrees,
        overlap_post={"high_overlap_pair_count": 34, "largest_collapse_component": 12},
        overlap_reduction_pct=0.02857,
        collapse_pre=12,
        collapse_post=12,
    )
    assert decision["primary_recommendation"] == "KEEP_SE_RD_SEPARATE_REFINE_HUBS"
    assert KEEP_FAMILY in decision["affected_families"]
    assert MERGED_LABEL in decision["affected_families"]


def test_decide_merge_se_rd_when_not_lexically_distinct():
    decision = decide_residual_recommendation(
        se_rd={
            "cosine": 0.93,
            "lexically_distinct": False,
            "shared_token_ratio": 0.2,
            "above_overlap_threshold": True,
        },
        degrees=[{"family": MERGED_LABEL, "degree": 7}],
        overlap_post={"high_overlap_pair_count": 34},
        overlap_reduction_pct=0.02,
        collapse_pre=12,
        collapse_post=12,
    )
    assert decision["primary_recommendation"] == "MERGE_SE_RD"


def test_assemble_residual_review():
    pairs = [
        {
            "cosine": 0.93,
            "family_a": MERGED_LABEL,
            "family_b": KEEP_FAMILY,
            "in_collapse_cluster": True,
        },
        {
            "cosine": 0.90,
            "family_a": "internet-slang",
            "family_b": MERGED_LABEL,
            "in_collapse_cluster": True,
        },
    ]
    degrees = degree_table(pairs)
    se_rd = analyze_se_rd(
        texts_se=["social status prestige hierarchy disapproval"],
        texts_rd=["romantic dating courtship partner relationship"],
        cosine=0.93,
    )
    assert se_rd["lexically_distinct"] is True
    decision = decide_residual_recommendation(
        se_rd=se_rd,
        degrees=degrees,
        overlap_post={
            "collapse_high_overlap_pairs": 30,
            "high_overlap_pair_count": 34,
            "largest_collapse_component": 12,
            "threshold": 0.8,
        },
        overlap_reduction_pct=0.02857,
        collapse_pre=12,
        collapse_post=12,
    )
    artifact = assemble_residual_review(
        {
            "degrees": degrees,
            "largest_component": [KEEP_FAMILY, MERGED_LABEL, "internet-slang"],
            "overlap_post": {
                "collapse_high_overlap_pairs": 30,
                "high_overlap_pair_count": 34,
                "largest_collapse_component": 12,
                "threshold": 0.8,
            },
            "overlap_pre": {
                "collapse_high_overlap_pairs": 33,
                "high_overlap_pair_count": 35,
                "largest_collapse_component": 12,
                "threshold": 0.8,
            },
            "overlap_reduction": {
                "absolute_reduction": 1,
                "percentage_reduction": 0.02857142857142857,
            },
            "recommendation": decision,
            "se_rd_analysis": se_rd,
            "top_pairs": pairs,
        }
    )
    assert artifact["training_gate"] == "CLOSED"
    assert artifact["applies_ontology_change"] is False
    assert artifact["primary_recommendation"] == "KEEP_SE_RD_SEPARATE_REFINE_HUBS"
    assert "APPLY_RESIDUAL_HUB_BOUNDARY_PASS" in artifact["next_engineering_action"]
    assert artifact["artifact_sha256"]
    assert artifact["relationship_dating_status"]["merged_automatically"] is False
