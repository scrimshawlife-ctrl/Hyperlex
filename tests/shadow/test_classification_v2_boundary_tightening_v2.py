"""Boundary tightening V2 tests. No training, no reserve, no BEST writes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY  # noqa: E402
from hyperlexical.classification_v2_boundary_tightening_v2 import (  # noqa: E402
    BEST_SHA,
    BOUNDARY_REDEFINITION_SHA,
    HIGH_OVERLAP_COSINE,
    MATERIAL_OVERLAP_REDUCTION,
    TIGHTEN_RULE,
    assess_structural_splits,
    assemble_tightening,
    build_final_keep_identities,
    classify_structural_keep_for_comparison,
    classify_unresolved_row,
    family_semantic_contract,
    training_gate_v2,
    tightening_contract,
)


def test_contract_pins_threshold_and_forbids_train():
    contract = tightening_contract()
    assert contract["rule"] == TIGHTEN_RULE
    assert contract["material_overlap_reduction"] == MATERIAL_OVERLAP_REDUCTION == 0.30
    assert contract["high_overlap_cosine"] == HIGH_OVERLAP_COSINE == 0.80
    assert contract["train"] is False
    assert contract["moves_best"] is False
    assert contract["reserve_scored"] is False
    assert contract["mutates_ontology"] is False
    assert contract["boundary_redefinition_sha256"] == BOUNDARY_REDEFINITION_SHA
    assert contract["best_sha256"] == BEST_SHA
    assert len(contract["structural_split_pairs"]) == 3


def test_family_semantics_and_unresolved_classifier():
    for family in ACTIVE_FAMILY_VOCABULARY:
        contract = family_semantic_contract(family)
        assert contract["required_core"]
        assert "explicit_exclusions" in contract
    keep = classify_unresolved_row(
        identity="abc",
        current_family="social-status",
        text="An honorific marking high prestige rank in a social hierarchy",
        prior_decision="REVIEW",
    )
    assert keep["decision"] == "KEEP"
    assert keep["reason_code"] == "required_core_established"
    drop = classify_unresolved_row(
        identity="def",
        current_family="approval-disapproval",
        text="A generic person term",
        prior_decision="REVIEW",
    )
    assert drop["decision"] == "DROP"
    amb = classify_unresolved_row(
        identity="ghi",
        current_family="approval-disapproval",
        text="A derogatory insult marking elite hierarchy standing",
        prior_decision="AMBIGUOUS",
    )
    assert amb["decision"] == "AMBIGUOUS"
    assert amb["collision_pair"] == "approval-disapproval||social-status"
    excl = classify_unresolved_row(
        identity="jkl",
        current_family="approval-disapproval",
        text="A term about social status and prestige rank only",
        prior_decision="REVIEW",
    )
    assert excl["decision"] == "DROP"
    assert excl["reason_code"] == "explicit_exclusion_violated"
    noise = classify_unresolved_row(
        identity="90544f171008d3cf" + "0" * 48,
        current_family="music-entertainment",
        text="A type of tuning",
        prior_decision="DROP",
    )
    assert noise["decision"] == "DROP"
    assert noise["reason_code"] == "preserved_phase_a_noise_audit"


def test_structural_keep_comparison_and_support_floor():
    override = classify_structural_keep_for_comparison(
        identity="keep1",
        current_family="social-status",
        text="A derogatory insult and pejorative disapproval of someone",
    )
    assert override is not None
    assert override["decision"] == "AMBIGUOUS"
    prior = [{"decision": "KEEP", "family": "social-status", "identity": "keep1"}]
    for i in range(12):
        prior.append({"decision": "KEEP", "family": "betting-sharp", "identity": f"bet{i}"})
        prior.append({"decision": "KEEP", "family": "internet-slang", "identity": f"isl{i}"})
        prior.append({"decision": "KEEP", "family": "memetic", "identity": f"mem{i}"})
    for family in ACTIVE_FAMILY_VOCABULARY:
        if family in {"social-status", "betting-sharp", "internet-slang", "memetic"}:
            continue
        prior.append({"decision": "KEEP", "family": family, "identity": f"{family}-1"})
    unresolved = [
        {
            "decision": "KEEP",
            "current_family": "social-status",
            "source_identity": "newkeep",
            "reason_code": "required_core_established",
        }
    ]
    built = build_final_keep_identities(
        prior_rows=prior,
        unresolved_results=unresolved,
        structural_keep_overrides=[override],
    )
    assert "keep1" not in built["keep_identities"]["social-status"]
    assert "newkeep" in built["keep_identities"]["social-status"]
    assert built["sparse_support_preserved"] is True


def test_gate_and_split_assessment():
    support = {family: 12 for family in ACTIVE_FAMILY_VOCABULARY}
    gate = training_gate_v2(
        pre_count=10,
        post_count=7,
        support=support,
        collapse_pre=13,
        collapse_post=10,
        support_floor_failure=False,
    )
    assert gate["overlap_reduction"] == 0.3
    assert gate["training_gate"] == "OPEN"
    assert gate["next_action"] == "TRAIN_CLASSIFICATION_V2"
    closed = training_gate_v2(
        pre_count=10,
        post_count=9,
        support=support,
        collapse_pre=13,
        collapse_post=12,
        support_floor_failure=False,
    )
    assert closed["training_gate"] == "CLOSED"
    splits = assess_structural_splits(
        pre_pairs=[{"family_a": "approval-disapproval", "family_b": "social-status"}],
        post_pairs=[{"family_a": "approval-disapproval", "family_b": "social-status"}],
    )
    assert splits[0]["status"] == "OVERLAP_REMAINS_STRUCTURAL"
    assert splits[0]["split_performed"] is False


def test_assemble_requires_nineteen_semantics():
    semantics = {family: family_semantic_contract(family) for family in ACTIVE_FAMILY_VOCABULARY}
    support = {family: 3 for family in ACTIVE_FAMILY_VOCABULARY}
    for family in ("betting-sharp", "internet-slang", "memetic"):
        support[family] = 12
    pre = {
        "high_overlap_pair_count": 10,
        "collapse_high_overlap_pairs": 8,
        "largest_collapse_component": 13,
        "threshold": 0.8,
    }
    post = {
        "high_overlap_pair_count": 6,
        "collapse_high_overlap_pairs": 4,
        "largest_collapse_component": 8,
        "threshold": 0.8,
    }
    gate = training_gate_v2(
        pre_count=10,
        post_count=6,
        support=support,
        collapse_pre=13,
        collapse_post=8,
        support_floor_failure=False,
    )
    artifact = assemble_tightening(
        {
            "family_semantics": semantics,
            "pairwise_discriminators": [],
            "unresolved_reclassifications": [],
            "structural_keep_overrides": [],
            "row_status_counts": {"KEEP": 1, "DROP": 1, "RELABEL_CANDIDATE": 0, "AMBIGUOUS": 0},
            "delta": {"prior_keep": 271},
            "support": support,
            "overlap_pre": pre,
            "overlap_post": post,
            "split_candidate_assessments": [],
            "training_gate": gate,
        }
    )
    assert artifact["boundary_tightening_state"] == "SEALED"
    assert artifact["train"] is False
    assert len(artifact["family_semantics"]) == 19
