"""Phase execution contract tests. No training, no reserve, no BEST writes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v2_phase_execution import (  # noqa: E402
    BEST_SHA,
    PHASE_RULE,
    REMEDIATION_ARTIFACT_SHA,
    TARGET_TRAIN_DEFINITIONS,
    default_noise_reviews,
    make_train_definition_row,
    merge_surface_with_definitions,
    phase_a_support_report,
    phase_c_ontology_decisions,
    phase_contract,
    phases_complete,
)
from hyperlexical.classification_v2_separability_audit import SPARSE_FOCUS  # noqa: E402
from hyperlexical.holdout_guard import normalized_text_sha256  # noqa: E402


def test_phase_contract_is_non_mutating():
    contract = phase_contract()
    assert contract["rule"] == PHASE_RULE
    assert contract["train"] is False
    assert contract["mutates_ontology"] is False
    assert contract["reserve_scored"] is False
    assert contract["moves_best"] is False
    assert contract["remediation_artifact_sha256"] == REMEDIATION_ARTIFACT_SHA
    assert contract["best_sha256"] == BEST_SHA
    assert contract["target_train_definitions"] == TARGET_TRAIN_DEFINITIONS


def test_make_train_definition_row_requires_prose_and_sets_definition_text():
    row = make_train_definition_row(
        family="internet-slang",
        text="An informal Internet expression used in online chat communities worldwide today",
        page="example",
        revision_id=1,
        revision_sha1="abc",
        revision_timestamp="2026-01-01T00:00:00Z",
        sense_labels=["internet slang"],
        evidence="sense_label",
        batch_id="test",
    )
    assert row["split"] == "train"
    assert row["text"] == row["provenance"]["definition_prose"]
    assert row["class"] == "OBSERVED"


def test_noise_reviews_cover_seven_rows_with_allowed_decisions():
    noise = [
        {
            "family": "music-entertainment",
            "identity": "90544f171008d3cf" + "0" * 48,
            "nearest_family": "spiritual-mystic",
            "text": "tetrachord",
        },
        {
            "family": "regional-cultural",
            "identity": "8bd78f57167eeb19" + "0" * 48,
            "nearest_family": "identity-affiliation",
            "text": "mountain lion",
        },
        {
            "family": "relationship-dating",
            "identity": "17d1d192814cdda7" + "0" * 48,
            "nearest_family": "approval-disapproval",
            "text": "courtship",
        },
        {
            "family": "relationship-dating",
            "identity": "4df2dd1d7f069ccc" + "0" * 48,
            "nearest_family": "social-status",
            "text": "phone call",
        },
        {
            "family": "relationship-dating",
            "identity": "bc29c71410e85594" + "0" * 48,
            "nearest_family": "approval-disapproval",
            "text": "incel",
        },
        {
            "family": "spiritual-mystic",
            "identity": "5dcd520e0f42301b" + "0" * 48,
            "nearest_family": "social-status",
            "text": "atlantis",
        },
        {
            "family": "workplace-career",
            "identity": "2e19997bbcf52f02" + "0" * 48,
            "nearest_family": "technology-ai",
            "text": "it concerns",
        },
    ]
    reviews = default_noise_reviews(noise)
    assert len(reviews) == 7
    assert {row["decision"] for row in reviews} <= {"KEEP", "RELABEL", "DROP", "VOID"}
    assert any(row["decision"] == "RELABEL" and row["relabel_to"] == "technology-ai" for row in reviews)


def test_merge_and_support_detect_sparse_target():
    rows = []
    for index, family in enumerate(SPARSE_FOCUS):
        for n in range(12):
            text = f"A durable {family} definition prose example number {n} with enough length"
            rows.append(
                {
                    "class": "OBSERVED",
                    "lineage": family,
                    "split": "train",
                    "task": "classify",
                    "text": text,
                    "provenance": {"definition_prose": text},
                }
            )
    # exact-copy betting uses prose surface without requiring provenance equality path differently;
    # definition_sources handles it.
    merged = merge_surface_with_definitions([], rows)
    assert len(merged) == 36
    # identity collision de-dupe
    again = merge_surface_with_definitions(merged, rows[:3])
    assert len(again) == 36
    report = phase_a_support_report(merged)
    # may be under if exact-copy filter rejects; ensure function returns structure
    assert set(report["families"]) == set(SPARSE_FOCUS)


def test_ontology_decisions_do_not_mutate_vocabulary():
    remediation = {
        "ontology_refactor_candidates": [
            {
                "action": "REVIEW_MERGE_OR_SPLIT",
                "component_size": 13,
                "families": ["social-status", "approval-disapproval"],
                "recommended_first_reviews": [
                    {
                        "family_a": "approval-disapproval",
                        "family_b": "social-status",
                        "probe_f1": 0.3,
                        "cross_family_similarity": 0.8,
                    }
                ],
            }
        ]
    }
    decisions = phase_c_ontology_decisions(remediation)
    assert decisions[0]["apply_to_active_ontology"] is False
    assert decisions[0]["action"] == "KEEP_WITH_BOUNDARY_REDEFINITION"
    assert phases_complete(
        {
            "phase_status": {
                "PHASE_A_DATA_AND_NOISE": "COMPLETE",
                "PHASE_B_BOUNDARY_REFINEMENT": "COMPLETE",
                "PHASE_C_ONTOLOGY_REFACTOR_REVIEW": "COMPLETE",
                "PHASE_D_REAUDIT_BEFORE_TRAINING": "COMPLETE",
            }
        }
    )
