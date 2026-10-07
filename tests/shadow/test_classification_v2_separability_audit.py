"""Separability audit contract tests. No training, no reserve, no BEST writes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

import hyperlexical.classification_v2 as _cv2  # noqa: E402
from hyperlexical.classification_v2_separability_audit import (  # noqa: E402
    ACTIVE_FAMILY_VOCABULARY,  # snapshot matching assemble_audit internal check
    AUDIT_DECISIONS,
    AUDIT_RULE,
    BEST_SHA,
    BOUNDARY_SHA,
    COLLAPSE_CLUSTER,
    REPAIR_PRIMARY_SHA,
    SEPARATION_SHA,
    SPARSE_FOCUS,
    assemble_audit,
    assemble_pair_matrices,
    audit_contract,
    classify_pair_flags,
    embedding_pair_report,
    family_status_for,
    lexical_pair_report,
    overall_decision,
    pairwise_probe,
    sparse_family_treatment,
)


def _axis(slot: int, dim: int = 8) -> list[float]:
    vector = [0.0] * dim
    vector[slot % dim] = 1.0
    return vector


def test_audit_contract_is_read_only_and_pins_geometry_inputs():
    contract = audit_contract()
    assert contract["rule"] == AUDIT_RULE
    assert contract["train"] is False
    assert contract["encoder_updated"] is False
    assert contract["reserve_scored"] is False
    assert contract["moves_best"] is False
    assert contract["jev"] == "OFF"
    assert contract["best_sha256"] == BEST_SHA
    assert contract["boundary_sha256"] == BOUNDARY_SHA
    assert contract["separation_sha256"] == SEPARATION_SHA
    assert contract["repair_primary_sha256"] == REPAIR_PRIMARY_SHA
    assert list(SPARSE_FOCUS) == ["betting-sharp", "internet-slang", "memetic"]
    assert len(COLLAPSE_CLUSTER) == 15
    assert "none" not in ACTIVE_FAMILY_VOCABULARY


def test_lexical_log_odds_separates_distinct_definition_prose():
    left = [
        "prestige status hierarchy elite social rank",
        "status climbing prestige ladder social rank",
    ]
    right = [
        "melody chorus performance concert entertainment",
        "stage performance melody chorus entertainment",
    ]
    report = lexical_pair_report(left, right)
    assert "prestige" in report["tokens_enriched_in_a"] or "status" in report["tokens_enriched_in_a"]
    assert "melody" in report["tokens_enriched_in_b"] or "chorus" in report["tokens_enriched_in_b"]
    assert report["shared_token_ratio"] < 0.45


def test_pairwise_probe_and_embedding_metrics_are_deterministic():
    left_train = [_axis(0), _axis(0), [_axis(0)[0] + 0.01] + _axis(0)[1:]]
    right_train = [_axis(1), _axis(1), [_axis(1)[0]] + [0.01] + _axis(1)[2:]]
    left_val = [_axis(0), _axis(0)]
    right_val = [_axis(1), _axis(1)]
    first = pairwise_probe(left_train, right_train, left_val, right_val)
    second = pairwise_probe(left_train, right_train, left_val, right_val)
    assert first == second
    assert first["status"] == "OK"
    assert first["f1"] is not None and first["f1"] >= 0.8
    sparse = pairwise_probe([_axis(0)], [_axis(1)], left_val, right_val)
    assert sparse["status"] == "NOT_COMPUTABLE"
    emb = embedding_pair_report(left_train, right_train, [_axis(0)], [_axis(1)])
    assert emb["cross_family_similarity"] is not None
    assert emb["centroid_distance"] is not None
    assert emb["anchor_collision_rate"] == 0.0


def test_collision_flags_and_family_status_cover_sparse_overlap_and_separable():
    sparse_flags = classify_pair_flags(
        n_a=1,
        n_b=6,
        lexical={
            "shared_token_ratio": 0.1,
            "tokens_enriched_in_a": ["meme", "template"],
            "tokens_enriched_in_b": ["status", "rank"],
        },
        embedding={
            "cross_family_similarity": 0.2,
            "centroid_distance": 0.8,
            "nearest_neighbor_confusion_a": 0.0,
            "nearest_neighbor_confusion_b": 0.0,
            "anchor_collision_rate": 0.0,
        },
        probe={"status": "NOT_COMPUTABLE", "f1": None},
    )
    assert "DATA_TOO_SPARSE" in sparse_flags
    overlap_flags = classify_pair_flags(
        n_a=6,
        n_b=6,
        lexical={
            "shared_token_ratio": 0.7,
            "tokens_enriched_in_a": [],
            "tokens_enriched_in_b": [],
        },
        embedding={
            "cross_family_similarity": 0.95,
            "centroid_distance": 0.05,
            "nearest_neighbor_confusion_a": 0.8,
            "nearest_neighbor_confusion_b": 0.7,
            "anchor_collision_rate": 1.0,
        },
        probe={"status": "OK", "f1": 0.4},
    )
    assert "ONTOLOGY_OVERLAP" in overlap_flags or "DEFINITION_TOO_GENERIC" in overlap_flags
    separable_flags = classify_pair_flags(
        n_a=6,
        n_b=6,
        lexical={
            "shared_token_ratio": 0.1,
            "tokens_enriched_in_a": ["status", "prestige"],
            "tokens_enriched_in_b": ["melody", "chorus"],
        },
        embedding={
            "cross_family_similarity": 0.1,
            "centroid_distance": 0.9,
            "nearest_neighbor_confusion_a": 0.0,
            "nearest_neighbor_confusion_b": 0.0,
            "anchor_collision_rate": 0.0,
        },
        probe={"status": "OK", "f1": 0.95},
    )
    assert separable_flags == ["SEPARABLE"]
    assert (
        family_status_for("memetic", n_train=1, pair_flags=[sparse_flags], noisy_rows=0)
        == "UNDER_SUPPORTED"
    )
    assert (
        family_status_for(
            "social-status",
            n_train=6,
            pair_flags=[overlap_flags for _ in range(8)],
            noisy_rows=0,
        )
        == "OVERLAPPING"
    )


def test_sparse_treatment_does_not_claim_ontology_failure_from_support_alone():
    treatment = sparse_family_treatment(
        "internet-slang",
        n_train=1,
        n_val=58,
        lexical_pair_best={
            "shared_token_ratio": 0.2,
            "tokens_enriched_in_a": ["slang", "internet", "meme", "chat"],
            "tokens_enriched_in_b": ["status", "rank", "prestige", "elite"],
        },
        probe_best=None,
    )
    assert treatment["ontology_failure_from_support_alone"] is False
    assert treatment["additional_data_plausibly_resolves"] is True


def test_overall_decision_and_assemble_audit_seal():
    statuses = {family: "OVERLAPPING" for family in ACTIVE_FAMILY_VOCABULARY}
    for family in SPARSE_FOCUS:
        statuses[family] = "UNDER_SUPPORTED"
    statuses["gaming-meta"] = "SEPARABLE"
    statuses["ai-native"] = "SEPARABLE"
    statuses["crypto-degen"] = "SEPARABLE"
    decision = overall_decision(
        statuses,
        {
            "ONTOLOGY_OVERLAP": 40,
            "DEFINITION_TOO_GENERIC": 50,
            "DATA_TOO_SPARSE": 30,
            "REPRESENTATION_COLLAPSE": 10,
        },
    )
    assert decision in AUDIT_DECISIONS
    assert decision == "MIXED_REMEDIATION_REQUIRED"
    pair_rows = [
        {
            "family_a": "internet-slang",
            "family_b": "memetic",
            "flags": ["ONTOLOGY_OVERLAP", "DEFINITION_TOO_GENERIC"],
            "embedding": {
                "anchor_collision_rate": 1.0,
                "centroid_distance": 0.01,
                "cross_family_similarity": 0.99,
                "nearest_neighbor_confusion_a": 0.8,
                "nearest_neighbor_confusion_b": 0.7,
                "within_family_similarity_a": 0.9,
                "within_family_similarity_b": 0.9,
            },
            "lexical": {
                "distinctive_phrases_a": [],
                "distinctive_phrases_b": [],
                "shared_high_frequency_tokens": ["person"],
                "shared_token_ratio": 0.8,
                "tokens_enriched_in_a": [],
                "tokens_enriched_in_b": [],
            },
            "probe": {"accuracy": 0.5, "f1": 0.4, "status": "OK"},
        }
    ]
    matrices = assemble_pair_matrices(ACTIVE_FAMILY_VOCABULARY, pair_rows)
    artifact = assemble_audit(
        {
            "boundary_evidence": [
                {
                    "family": family,
                    "positive_semantic_cues": [],
                    "nearest_competing_families": [],
                    "distinguishing_cues": {},
                    "shared_overlapping_cues": {},
                    "exclusion_cues": [],
                    "ambiguous_training_rows": [],
                    "boundary_violating_rows": [],
                }
                for family in ACTIVE_FAMILY_VOCABULARY
            ],
            "decision": decision,
            "embedding_matrix_sha256": matrices["embedding_matrix_sha256"],
            "family_status": statuses,
            "lexical_matrix_sha256": matrices["lexical_matrix_sha256"],
            "pair_flag_counts": {"ONTOLOGY_OVERLAP": 40},
            "pair_rows": pair_rows,
            "proposed_boundary_refinements": [],
            "remediation": [
                {"family": family, "actions": ["boundary refinement"], "status": statuses[family]}
                for family in ACTIVE_FAMILY_VOCABULARY
                if statuses[family] != "SEPARABLE"
            ],
            "sparse_treatment": [
                sparse_family_treatment(
                    family,
                    n_train=1,
                    n_val=2,
                    lexical_pair_best=None,
                    probe_best=None,
                )
                for family in SPARSE_FOCUS
            ],
            "support": {
                family: {"observed": 1, "inferred": 0, "n": 1} for family in ACTIVE_FAMILY_VOCABULARY
            },
            "suspected_label_noise": [],
            "worst_collision_pairs": pair_rows,
        }
    )
    assert artifact["audit_state"] == "SEALED"
    assert artifact["train"] is False
    assert artifact["reserve_scored"] is False
    assert artifact["moves_best"] is False
    assert artifact["best_sha256"] == BEST_SHA
    assert len(artifact["artifact_sha256"]) == 64
