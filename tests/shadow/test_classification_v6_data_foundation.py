"""CPU tests for V6 data-foundation contracts."""

from __future__ import annotations

from hyperlexical.classification_v5_stage_a_gold_identifiability_contract import (
    CONTRACT_ID as GOLD_CONTRACT_ID,
)
from hyperlexical.classification_v6_data_foundation import (
    FOUNDATION_ID,
    MAX_FAMILY_SHARE_TRAIN,
    NEXT_ACQUIRE,
    NEXT_ONTOLOGY,
    NEXT_READY,
    OPERATING_DISTRIBUTION_ID,
    PHASE_RULE,
    QUALIFICATION_HOLD_ID,
    READY_GATES,
    build_foundation_receipt,
    classify_ontology_pair,
    evaluation_contract_v1,
    foundation_disposition,
    gold_contract_binding,
    operating_distribution_v1,
    representation_viability,
    retrieval_viability,
    summarize_split_rows,
)
from hyperlexical.classification_v6_v5_research_baseline import (
    BASELINE_ID,
    RELEASE_QUALIFIED,
    v5_research_baseline,
)


def test_v5_baseline_not_release_qualified():
    base = v5_research_baseline()
    assert base["BASELINE_ID"] == BASELINE_ID
    assert base["RELEASE_QUALIFIED"] is False
    assert RELEASE_QUALIFIED is False
    assert "V5 is not release-qualified." in base["statement"]


def test_operating_distribution_and_roles():
    assert PHASE_RULE.startswith("BUILD_REPRESENTATIVE_V6")
    assert FOUNDATION_ID.startswith("HYPERLEX_V6")
    op = operating_distribution_v1()
    assert op["OPERATING_DISTRIBUTION_ID"] == OPERATING_DISTRIBUTION_ID
    assert op["gold_identifiability_contract"] == GOLD_CONTRACT_ID
    assert op["expected_family_mix"]["bounded_train_max_share"] == MAX_FAMILY_SHARE_TRAIN
    assert gold_contract_binding()["auto_relabel"] is False
    assert QUALIFICATION_HOLD_ID.endswith("QUALIFICATION_001")
    ev = evaluation_contract_v1()
    assert "false_entry" in ev["stage_a"]
    assert ev["distribution_shift_reporting"]["large_delta_is_first_class_failure_signal"]


def test_viability_and_disposition_helpers():
    assert classify_ontology_pair(
        definition_overlap=0.1,
        embedding_overlap=0.5,
        lexical_overlap=0.1,
        boundary_clarity=0.9,
    ) == "CLEARLY_SEPARABLE"
    assert classify_ontology_pair(
        definition_overlap=0.8,
        embedding_overlap=0.91,
        lexical_overlap=0.5,
        boundary_clarity=0.2,
    ) == "ONTOLOGY_REVIEW_REQUIRED"
    assert (
        representation_viability(
            present_none_centroid_cosine=0.95,
            within_family_sim=0.6,
            between_family_sim=0.85,
            nearest_family_purity=0.1,
        )
        == "BASE_REPRESENTATION_INADEQUATE"
    )
    assert (
        retrieval_viability(family_precision=0.2, top1=0.1, coverage=0.2)
        == "RETRIEVAL_NOT_VIABLE"
    )

    all_ready = {g: True for g in READY_GATES}
    ready = foundation_disposition(all_ready, ontology_structurally_broken=False)
    assert ready["V6_DATA_FOUNDATION_STATE"] == "V6_DATA_FOUNDATION_READY"
    assert ready["NEXT_ACTION"] == NEXT_READY
    onto = foundation_disposition(all_ready, ontology_structurally_broken=True)
    assert onto["NEXT_ACTION"] == NEXT_ONTOLOGY
    partial = foundation_disposition(
        {**all_ready, "TRAIN_READY": False}, ontology_structurally_broken=False
    )
    assert partial["V6_DATA_FOUNDATION_STATE"] == "V6_DATA_FOUNDATION_PARTIAL"
    assert partial["NEXT_ACTION"] == NEXT_ACQUIRE

    rows = [
        {
            "evidence_label": "EVIDENCE_PRESENT",
            "gold_family": "memetic",
            "provenance": "OBSERVED",
            "construction_tag": "NATURAL",
            "source_family": "wikt",
            "text": "abc",
        }
    ]
    summary = summarize_split_rows(rows)
    assert summary["n"] == 1
    assert summary["observed_share"] == 1.0

    receipt = build_foundation_receipt(
        code_revision="deadbeef",
        audit={"ontology_structurally_broken": False},
        gates=all_ready,
        settled_at="2026-10-01T00:00:00Z",
    )
    assert receipt["TRAIN"] is False
    assert receipt["V6_DATA_FOUNDATION_RECEIPT_SHA256"]
