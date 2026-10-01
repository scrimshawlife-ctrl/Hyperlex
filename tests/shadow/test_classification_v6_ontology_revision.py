"""CPU tests for V6 ontology redesign contracts."""

from __future__ import annotations

from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY
from hyperlexical.classification_v6_ontology_revision import (
    FAMILY_PURPOSE,
    HISTORICAL_ONTOLOGY_STATE,
    NEXT_HUMAN,
    NEXT_REBUILD,
    PHASE_RULE,
    build_ontology_receipt,
    candidate_structures,
    estimate_multilabel_fractions,
    geometry_cluster_id,
    historical_ontology_freeze,
    migration_map,
    ontology_disposition,
    pairwise_boundary_matrix,
    preferred_ontology,
    semantic_level_diagnosis,
    stage_b_task_spec,
)


def test_historical_freeze_and_purpose_coverage():
    hist = historical_ontology_freeze()
    assert hist["state"] == HISTORICAL_ONTOLOGY_STATE
    assert hist["mutable"] is False
    assert set(FAMILY_PURPOSE) == set(ACTIVE_FAMILY_VOCABULARY)
    unclear = [
        f for f, v in FAMILY_PURPOSE.items() if v["purpose_status"] == "PURPOSE_UNCLEAR"
    ]
    assert "regional-cultural" in unclear
    assert "identity-affiliation" in unclear


def test_preferred_hierarchical_multilabel():
    diag = semantic_level_diagnosis()
    assert diag["dominant_level_in_current_ontology"] == "MIXED_DOMAIN_AND_PRAGMATIC"
    pref = preferred_ontology()
    assert pref["structure"] == "HIERARCHICAL_MULTI_LABEL"
    assert candidate_structures()["D_hierarchical_multi_label"]["preferred"] is True
    assert stage_b_task_spec()["task"] == "HIERARCHICAL_MULTI_LABEL"
    assert geometry_cluster_id("ai-native") == "domain.technology.ai_discourse"
    assert geometry_cluster_id("regional-cultural") is None
    states = {m["from"]: m["state"] for m in migration_map()}
    assert states["technology-ai"] == "PARENT"
    assert states["ai-native"] == "CHILD"


def test_pairwise_and_disposition():
    pairs = pairwise_boundary_matrix()
    assert len(pairs) == len(ACTIVE_FAMILY_VOCABULARY) * (len(ACTIVE_FAMILY_VOCABULARY) - 1) // 2
    tech = [
        p
        for p in pairs
        if {p["a"], p["b"]} == {"technology-ai", "ai-native"}
    ][0]
    assert tech["class"] == "HIERARCHICAL"
    blocked = ontology_disposition(
        structure_chosen=True,
        definitions_frozen=True,
        migration_sealed=True,
        cardinality_frozen=True,
        identifiability_checked=True,
        support_viable=True,
        remaining_human_critical=True,
        task_impossible=False,
    )
    assert blocked["V6_ONTOLOGY_STATE"] == "V6_ONTOLOGY_BLOCKED_ON_HUMAN_AGREEMENT"
    assert blocked["NEXT_ACTION"] == NEXT_HUMAN
    ready = ontology_disposition(
        structure_chosen=True,
        definitions_frozen=True,
        migration_sealed=True,
        cardinality_frozen=True,
        identifiability_checked=True,
        support_viable=True,
        remaining_human_critical=False,
        task_impossible=False,
    )
    assert ready["NEXT_ACTION"] == NEXT_REBUILD

    frac = estimate_multilabel_fractions(
        [
            {
                "evidence_label": "EVIDENCE_PRESENT",
                "text": "A meme insult on reddit about the gaming meta nerf.",
                "gold_family": "memetic",
            }
        ]
    )
    assert frac["n_present"] == 1
    assert PHASE_RULE.startswith("REVISE_HYPERLEX_V6")
    receipt = build_ontology_receipt(
        code_revision="deadbeef",
        audit={"support_viable": True, "remaining_human_critical": True},
        settled_at="2026-10-01T00:00:00Z",
    )
    assert receipt["TRAIN"] is False
    assert receipt["QUAL_ROWS_INSPECTED"] is False
    assert receipt["V6_ONTOLOGY_REVISION_RECEIPT_SHA256"]
