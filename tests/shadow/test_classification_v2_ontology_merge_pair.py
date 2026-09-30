"""APPLY_ONTOLOGY_MERGE_PAIR tests. No training, reserve scoring, or BEST moves."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY  # noqa: E402
from hyperlexical.classification_v2_ontology_merge_pair import (  # noqa: E402
    EXPECTED_MIGRATED_TRAIN,
    EXPECTED_MIGRATED_VAL,
    EXPECTED_RD_TRAIN,
    EXPECTED_RD_VAL,
    EXPECTED_SE_TRAIN,
    EXPECTED_SE_VAL,
    FORWARD_ACTIVE_FAMILY_VOCABULARY,
    FORWARD_COLLAPSE_CLUSTER,
    FORWARD_VOCABULARY_ID,
    KEEP_FAMILY,
    MERGE_RULE,
    MERGED_LABEL,
    ONTOLOGY_REVIEW_SHA,
    PRE_MERGE_OVERLAP_PIN,
    SOURCE_MERGE_FAMILIES,
    assemble_merge_artifact,
    existing_overlap_gate_pass,
    forward_ontology_identity,
    freeze_migration_map,
    head_initialization_policy,
    merge_contract,
    migrate_forward_rows,
    overlap_reduction,
    relationship_dating_post_merge_status,
    training_gate_from_readiness,
    verify_migration_counts,
    forward_support_readiness,
)


def test_contract_and_forward_vocab():
    contract = merge_contract()
    assert contract["rule"] == MERGE_RULE
    assert contract["train"] is False
    assert contract["moves_best"] is False
    assert contract["reserve_scored"] is False
    assert contract["applies_ontology_change"] is True
    assert contract["historical_vocabulary_mutated"] is False
    assert contract["merges_relationship_dating"] is False
    assert contract["jev"] == "OFF"
    assert contract["ontology_review_sha256"] == ONTOLOGY_REVIEW_SHA
    assert len(FORWARD_ACTIVE_FAMILY_VOCABULARY) == 18
    assert MERGED_LABEL in FORWARD_ACTIVE_FAMILY_VOCABULARY
    assert KEEP_FAMILY in FORWARD_ACTIVE_FAMILY_VOCABULARY
    for family in SOURCE_MERGE_FAMILIES:
        assert family not in FORWARD_ACTIVE_FAMILY_VOCABULARY
    # Historical vocabulary untouched.
    assert "approval-disapproval" in ACTIVE_FAMILY_VOCABULARY
    assert "social-status" in ACTIVE_FAMILY_VOCABULARY
    assert MERGED_LABEL not in ACTIVE_FAMILY_VOCABULARY
    assert MERGED_LABEL in FORWARD_COLLAPSE_CLUSTER
    assert "approval-disapproval" not in FORWARD_COLLAPSE_CLUSTER
    assert "social-status" not in FORWARD_COLLAPSE_CLUSTER


def test_migration_map_and_ontology_hash():
    migration = freeze_migration_map()
    assert migration["focus_migration"]["approval-disapproval"] == MERGED_LABEL
    assert migration["focus_migration"]["social-status"] == MERGED_LABEL
    assert migration["focus_migration"]["relationship-dating"] == KEEP_FAMILY
    assert migration["compatibility_map"]["gaming-meta"] == "gaming-meta"
    assert migration["migration_map_sha256"]
    ontology = forward_ontology_identity()
    assert ontology["vocabulary_id"] == FORWARD_VOCABULARY_ID
    assert ontology["active_family_count"] == 18
    assert ontology["historical_vocabulary_mutated"] is False
    assert ontology["ontology_sha256"]
    init = head_initialization_policy()
    assert init[MERGED_LABEL]["mode"] == "SEMANTIC_PROTOTYPE_FROM_TRAINING_DEFINITIONS"
    assert init[MERGED_LABEL]["legacy_row_claim"] is False


def test_migrate_rows_and_verify_counts():
    migration = freeze_migration_map()
    rows = [
        {"lineage": "approval-disapproval", "split": "train", "task": "classify", "text": "a"},
        {"lineage": "social-status", "split": "train", "task": "classify", "text": "b"},
        {"lineage": "approval-disapproval", "split": "val", "task": "classify", "text": "c"},
        {"lineage": "relationship-dating", "split": "train", "task": "classify", "text": "d"},
        {"lineage": "gaming-meta", "split": "train", "task": "classify", "text": "e"},
        {"lineage": "approval-disapproval", "split": "test", "task": "classify", "text": "f"},
    ]
    result = migrate_forward_rows(rows, migration_map=migration["compatibility_map"])
    assert result["affected_train"] == 2
    assert result["affected_val"] == 1
    lineages = [row["lineage"] for row in result["rows"]]
    assert lineages.count(MERGED_LABEL) == 3
    assert "approval-disapproval" in lineages  # test split untouched
    assert result["rows"][0]["legacy_lineage"] == "approval-disapproval"

    ok = verify_migration_counts(
        definition_train={MERGED_LABEL: EXPECTED_SE_TRAIN, KEEP_FAMILY: EXPECTED_RD_TRAIN},
        definition_val={MERGED_LABEL: EXPECTED_SE_VAL, KEEP_FAMILY: EXPECTED_RD_VAL},
    )
    assert ok["ok"] is True
    assert ok["migrated_train"] == EXPECTED_MIGRATED_TRAIN
    assert ok["migrated_val"] == EXPECTED_MIGRATED_VAL

    bad = verify_migration_counts(
        definition_train={MERGED_LABEL: 11, KEEP_FAMILY: 5},
        definition_val={MERGED_LABEL: 4, KEEP_FAMILY: 2},
    )
    assert bad["ok"] is False


def test_overlap_gate_and_rd_status():
    pre = dict(PRE_MERGE_OVERLAP_PIN)
    post = {
        "collapse_high_overlap_pairs": 20,
        "high_overlap_pair_count": 20,
        "largest_collapse_component": 10,
        "threshold": 0.80,
        "high_overlap_pairs": [
            {"family_a": KEEP_FAMILY, "family_b": MERGED_LABEL, "cosine": 0.85},
            {"family_a": "memetic", "family_b": MERGED_LABEL, "cosine": 0.81},
        ],
    }
    reduction = overlap_reduction(pre, post)
    assert reduction["absolute_reduction"] == 15
    assert reduction["percentage_reduction"] == 15 / 35
    support = {family: 2 for family in FORWARD_ACTIVE_FAMILY_VOCABULARY}
    gate = existing_overlap_gate_pass(
        reduction=reduction, support=support, vocabulary=FORWARD_ACTIVE_FAMILY_VOCABULARY
    )
    assert gate["overlap_gate"] == "PASS"
    rd = relationship_dating_post_merge_status(post)
    assert rd["future_ontology_refactor_candidate"] is True
    assert rd["merged_in_this_pass"] is False


def test_readiness_and_assemble():
    vocab = FORWARD_ACTIVE_FAMILY_VOCABULARY
    train = {family: 2 for family in vocab}
    val = {family: 1 for family in vocab}
    ontology = forward_ontology_identity()
    migration = freeze_migration_map()
    reduction = overlap_reduction(
        PRE_MERGE_OVERLAP_PIN,
        {
            "collapse_high_overlap_pairs": 10,
            "high_overlap_pair_count": 10,
            "largest_collapse_component": 8,
            "threshold": 0.8,
        },
    )
    gate = existing_overlap_gate_pass(
        reduction=reduction, support=train, vocabulary=vocab
    )
    readiness = forward_support_readiness(
        train_support=train,
        val_support=val,
        ontology=ontology,
        migration=migration,
        boundary_assessment={"pass": True, "boundary_sha256": "b" * 64},
        overlap_gate=gate,
        isolation_pass=True,
        train_eval_separation_pass=True,
        vocabulary=vocab,
    )
    assert readiness["ready"] is True
    tg = training_gate_from_readiness(readiness, gate)
    assert tg["training_gate"] == "OPEN"
    assert tg["next_action"] == "TRAIN_CLASSIFICATION_V2"

    verification = verify_migration_counts(
        definition_train={MERGED_LABEL: 12, KEEP_FAMILY: 5, **{f: 1 for f in vocab if f not in {MERGED_LABEL, KEEP_FAMILY}}},
        definition_val={MERGED_LABEL: 4, KEEP_FAMILY: 2, **{f: 1 for f in vocab if f not in {MERGED_LABEL, KEEP_FAMILY}}},
    )
    artifact = assemble_merge_artifact(
        {
            "ontology": ontology,
            "migration": migration,
            "migration_verification": verification,
            "boundary": {"boundary_sha256": "b" * 64, "separation_sha256": "s" * 64, "pass": True},
            "overlap_pre": PRE_MERGE_OVERLAP_PIN,
            "overlap_post": {
                "collapse_high_overlap_pairs": 10,
                "high_overlap_pair_count": 10,
                "largest_collapse_component": 8,
                "threshold": 0.8,
                "high_overlap_pairs": [],
            },
            "overlap_reduction": reduction,
            "overlap_gate": gate,
            "readiness": readiness,
            "training_gate": tg,
            "relationship_dating_status": relationship_dating_post_merge_status(
                {"high_overlap_pairs": []}
            ),
            "head_initialization": head_initialization_policy(),
            "export_path": "/tmp/civilian.v0.6.merge.jsonl",
            "export_sha256": "e" * 64,
        }
    )
    assert artifact["merge_application_state"] == "APPLIED"
    assert artifact["active_family_count"] == 18
    assert artifact["artifact_sha256"]
    assert artifact["train"] is False
    assert artifact["moves_best"] is False
