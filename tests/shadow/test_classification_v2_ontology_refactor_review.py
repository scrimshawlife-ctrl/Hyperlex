"""Ontology refactor review tests. No training, no reserve, no BEST writes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v2_ontology_refactor_review import (  # noqa: E402
    BEST_SHA,
    FOCUS_FAMILIES,
    MERGED_LABEL,
    PROBE_LEARNABLE_F1,
    REVIEW_RULE,
    TIGHTENING_V2_SHA,
    analyze_pair,
    assemble_ontology_review,
    build_migration_mapping,
    build_semantic_definitions,
    decide_recommendation,
    review_contract,
    summarize_family,
)


def test_contract_forbids_train_and_auto_apply():
    contract = review_contract()
    assert contract["rule"] == REVIEW_RULE
    assert contract["train"] is False
    assert contract["moves_best"] is False
    assert contract["reserve_scored"] is False
    assert contract["applies_ontology_change"] is False
    assert contract["opens_training_gate"] is False
    assert contract["historical_artifacts_rewritten"] is False
    assert contract["best_sha256"] == BEST_SHA
    assert contract["boundary_tightening_v2_sha256"] == TIGHTENING_V2_SHA
    assert contract["probe_learnable_f1"] == PROBE_LEARNABLE_F1 == 0.60
    assert list(contract["focus_families"]) == list(FOCUS_FAMILIES)


def test_decide_merge_pair_when_ad_ss_unlearnable_and_rd_distinct():
    def pair(a, b, *, learnable, lex, collapsed, f1=0.33, cos=0.91):
        return {
            "family_a": a,
            "family_b": b,
            "learnable": learnable,
            "lexically_distinct": lex,
            "representation_collapsed": collapsed,
            "pairwise_probe_separability": {"f1": f1},
            "boundary_overlap": {"centroid_cosine": cos},
        }

    decision = decide_recommendation(
        [
            pair("approval-disapproval", "social-status", learnable=False, lex=True, collapsed=True),
            pair("approval-disapproval", "relationship-dating", learnable=False, lex=True, collapsed=True, cos=0.86),
            pair("relationship-dating", "social-status", learnable=False, lex=True, collapsed=True, cos=0.84),
        ]
    )
    assert decision["primary_recommendation"] == "MERGE_PAIR"
    assert set(decision["affected_families"]) == {"approval-disapproval", "social-status"}
    assert MERGED_LABEL in decision["proposed_resulting_labels"]
    assert "relationship-dating" in decision["proposed_resulting_labels"]
    mapping = build_migration_mapping(decision)
    assert mapping["migration_mapping"]["approval-disapproval"] == MERGED_LABEL
    assert mapping["migration_mapping"]["social-status"] == MERGED_LABEL
    assert mapping["migration_mapping"]["relationship-dating"] == "relationship-dating"
    assert mapping["compatibility_map"]["approval-disapproval"] == MERGED_LABEL
    defs = build_semantic_definitions(decision)
    assert MERGED_LABEL in defs
    assert "relationship-dating" in defs


def test_keep_separate_when_all_learnable():
    def pair(a, b):
        return {
            "family_a": a,
            "family_b": b,
            "learnable": True,
            "lexically_distinct": True,
            "representation_collapsed": False,
            "pairwise_probe_separability": {"f1": 0.8},
            "boundary_overlap": {"centroid_cosine": 0.5},
        }

    decision = decide_recommendation(
        [
            pair("approval-disapproval", "social-status"),
            pair("approval-disapproval", "relationship-dating"),
            pair("relationship-dating", "social-status"),
        ]
    )
    assert decision["primary_recommendation"] == "KEEP_SEPARATE"


def test_analyze_pair_and_assemble():
    summary_a = summarize_family(
        "social-status",
        contract={"required_semantic_core": ["status", "rank"], "positive_cues": ["social"], "exclusion_cues": []},
        texts=["Someone of high rank or social status", "lowest social status bumpkins"],
        pair_rows=[],
    )
    summary_b = summarize_family(
        "relationship-dating",
        contract={"required_semantic_core": ["romantic", "dating"], "positive_cues": ["courtship"], "exclusion_cues": []},
        texts=["A romantic relationship", "To play at courtship"],
        pair_rows=[],
    )
    analysis = analyze_pair(
        "social-status",
        "relationship-dating",
        texts_a=["Someone of high rank or social status", "lowest social status bumpkins"],
        texts_b=["A romantic relationship", "To play at courtship"],
        summary_a=summary_a,
        summary_b=summary_b,
        sealed_pair={
            "family_a": "social-status",
            "family_b": "relationship-dating",
            "flags": ["REPRESENTATION_COLLAPSE", "ONTOLOGY_OVERLAP"],
            "embedding": {"centroid_cosine": 0.84, "cross_family_similarity": 0.69},
            "probe": {"status": "OK", "f1": 0.33, "accuracy": 0.5, "n_train": 11, "n_val": 4},
        },
    )
    assert analysis["lexically_distinct"] is True
    assert analysis["learnable"] is False
    decision = {
        "affected_families": ["approval-disapproval", "social-status"],
        "primary_recommendation": "MERGE_PAIR",
        "proposed_resulting_labels": [MERGED_LABEL, "relationship-dating"],
        "rationale": "test",
    }
    migration = build_migration_mapping(decision)
    artifact = assemble_ontology_review(
        {
            "family_summaries": {
                "approval-disapproval": summary_a,
                "social-status": summary_a,
                "relationship-dating": summary_b,
            },
            "pairwise_analyses": [analysis],
            "recommendation": decision,
            "semantic_definitions": build_semantic_definitions(decision),
            "migration": migration,
            "impacts": {
                "rows_affected_train": 12,
                "training_gate_remains_closed": True,
            },
        }
    )
    assert artifact["ontology_review_state"] == "SEALED"
    assert artifact["primary_recommendation"] == "MERGE_PAIR"
    assert artifact["train"] is False
    assert artifact["opens_training_gate"] is False
    assert artifact["applies_ontology_change"] is False
    assert "APPLY_ONTOLOGY_MERGE_PAIR" in artifact["next_engineering_action"]
