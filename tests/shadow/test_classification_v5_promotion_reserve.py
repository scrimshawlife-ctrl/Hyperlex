"""Unit tests for V5 promotion reserve seal + one-shot score contracts."""

from __future__ import annotations

from hyperlexical.classification_v5_promotion_reserve import (
    MINIMUM_FAMILY_MARGIN,
    MINIMUM_FAMILY_SCORE,
    RESERVE_FLOORS,
    RESERVE_ID,
    audit_reserve_composition,
    audit_reserve_disjointness,
    classify_wrong_family_emission,
    decide_settlement,
    mark_evaluation_spent,
    next_action_for_settlement,
    normalize_reserve_row,
    reserve_contract,
    score_reserve_rows,
    seal_reserve,
)
from hyperlexical.holdout_guard import normalized_text_sha256


def _present(text: str, family: str, *, provenance: str = "OBSERVED") -> dict:
    return normalize_reserve_row(
        {
            "text": text,
            "evidence_subtype": "POSITIVE_EVIDENCE",
            "candidate_families": [family],
            "provenance": provenance,
            "label_authority": "HUMAN_SETTLED",
            "label_derivation": "semantic_source_evidence",
            "rights": "CC-BY-SA",
        }
    )


def _none(text: str, subtype: str, *, provenance: str = "OBSERVED") -> dict:
    return normalize_reserve_row(
        {
            "text": text,
            "evidence_subtype": subtype,
            "provenance": provenance,
            "label_authority": "HUMAN_SETTLED",
            "label_derivation": "semantic_source_evidence",
            "rights": "CC-BY-SA",
        }
    )


def _uncertain(text: str) -> dict:
    return normalize_reserve_row(
        {
            "text": text,
            "evidence_subtype": "AMBIGUOUS_EVIDENCE",
            "ambiguity_reason": "MULTIPLE_PLAUSIBLE_INTERPRETATIONS",
            "provenance": "OBSERVED",
            "label_authority": "HUMAN_SETTLED",
            "label_derivation": "semantic_source_evidence",
            "rights": "CC-BY-SA",
            "candidate_families": ["internet-slang"],
        }
    )


def _balanced_rows() -> list[dict]:
    families = [
        "betting-sharp",
        "conflict-aggression",
        "crypto-degen",
        "fashion-aesthetic",
        "gaming-meta",
        "identity-affiliation",
        "internet-slang",
        "memetic",
        "music-entertainment",
        "politics-civic",
        "regional-cultural",
        "relationship-dating",
        "social-evaluation",
        "spiritual-mystic",
        "sports-competition",
        "technology-ai",
        "workplace-career",
    ]
    rows: list[dict] = []
    # 8 per family = 136 PRESENT OBSERVED
    for family in families:
        for i in range(8):
            rows.append(
                _present(
                    f"Observed {family} attestation number {i} with durable cues.",
                    family,
                )
            )
    # NONE coverage
    for i in range(24):
        rows.append(
            _none(
                f"Ordinary domain botanical description without slang {i}.",
                "ORDINARY_DOMAIN_NONE",
            )
        )
    for i in range(12):
        rows.append(_none(f"Hard none residue without family evidence {i}.", "HARD_NONE"))
    for i in range(12):
        rows.append(
            _none(f"Near domain chat without family emission cues {i}.", "NEAR_DOMAIN_NONE")
        )
    for i in range(8):
        rows.append(
            _none(
                f"Generic errands prose without jargon {i}.",
                "GENERIC_NONE",
                provenance="INFERRED",
            )
        )
    for i in range(8):
        rows.append(
            _none(
                f"Lookalike residue ordinary documentation {i}.",
                "LEXICAL_LOOKALIKE_NONE",
                provenance="INFERRED",
            )
        )
    for i in range(8):
        rows.append(
            _none(f"zx{i}q", "SHORT_ATOM_NONE", provenance="INFERRED")
        )
    for i in range(30):
        rows.append(
            _uncertain(
                f"Ambiguous attestation alternatively admits slang or ordinary {i}."
            )
        )
    return rows


def test_contract_pins_frozen_stack():
    contract = reserve_contract()
    assert contract["reserve_id"] == RESERVE_ID
    assert contract["floors"] == RESERVE_FLOORS
    assert contract["frozen_thresholds"]["minimum_family_score"] == MINIMUM_FAMILY_SCORE
    assert contract["frozen_thresholds"]["minimum_family_margin"] == MINIMUM_FAMILY_MARGIN
    assert contract["train"] is False
    assert contract["rebuild_index"] is False


def test_composition_and_seal():
    rows = _balanced_rows()
    composition = audit_reserve_composition(rows)
    assert composition["composition_pass"], composition["reasons"]
    assert composition["n"] >= 200
    sealed = seal_reserve(rows)
    assert sealed["seal"]["immutable"] is True
    assert sealed["manifest"]["n"] == len(rows)
    assert len(sealed["seal"]["seal_sha256"]) == 64


def test_disjointness_detects_blocked_identity():
    rows = _balanced_rows()[:5]
    blocked = {rows[0]["identity"]: "v1r9"}
    report = audit_reserve_disjointness(rows, blocked=blocked)
    assert report["disjoint_pass"] is False
    assert report["n_blocked_hits"] >= 1


def test_score_settlement_pass_and_fail():
    # Synthetic score rows: perfect NONE rejection + precise family emissions.
    score_rows = []
    for i in range(60):
        score_rows.append(
            {
                "identity": normalized_text_sha256(f"none-{i}"),
                "evidence_label": "NO_EVIDENCE",
                "evidence_subtype": "HARD_NONE",
                "evidence_decision": "NO_EVIDENCE",
                "gold_decision_type": "NONE",
                "gold_family": None,
                "p_possible": 0.1,
                "p_confirmed": 0.1,
                "top1_family": "memetic",
                "top1_score": 0.9,
                "top2_family": "internet-slang",
                "top2_score": 0.1,
            }
        )
    for i in range(20):
        score_rows.append(
            {
                "identity": normalized_text_sha256(f"family-{i}"),
                "evidence_label": "EVIDENCE_PRESENT",
                "evidence_subtype": "POSITIVE_EVIDENCE",
                "evidence_decision": "EVIDENCE_PRESENT",
                "gold_decision_type": "FAMILY",
                "gold_family": "memetic",
                "p_possible": 0.9,
                "p_confirmed": 0.8,
                "top1_family": "memetic",
                "top1_score": 0.9,
                "top2_family": "internet-slang",
                "top2_score": 0.1,
            }
        )
    metrics = score_reserve_rows(score_rows)
    assert metrics["primary_gate_pass"] is True
    assert metrics["secondary_gate_pass"] is True
    assert metrics["settlement"] == "RESERVE_PASS"

    # Inject false entries to fail primary gate.
    for i in range(10):
        score_rows[i]["evidence_decision"] = "EVIDENCE_PRESENT"
    fail_metrics = score_reserve_rows(score_rows)
    assert fail_metrics["primary_gate_pass"] is False
    assert fail_metrics["settlement"] == "RESERVE_FAIL"


def test_wrong_emission_classification():
    assert (
        classify_wrong_family_emission(
            gold_evidence_label="NO_EVIDENCE",
            gold_family=None,
            predicted_family="memetic",
        )
        == "STAGE_A_FALSE_ENTRY"
    )
    assert (
        classify_wrong_family_emission(
            gold_evidence_label="EVIDENCE_PRESENT",
            gold_family="memetic",
            predicted_family="internet-slang",
        )
        == "STAGE_B_WRONG_FAMILY"
    )


def test_evaluation_spent_and_next_action():
    rows = mark_evaluation_spent(_balanced_rows()[:3])
    assert all(row["evaluation_spent"] is True for row in rows)
    assert "PRODUCTION_PROMOTION_ELIGIBLE" in next_action_for_settlement("RESERVE_PASS")
    assert decide_settlement(
        composition={"composition_pass": False},
        disjointness={"disjoint_pass": True},
        metrics=None,
    ) == "RESERVE_INVALID"
