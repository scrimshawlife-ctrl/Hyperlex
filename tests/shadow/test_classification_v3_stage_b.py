"""Stage B retrieval wiring tests. No GPU / reserve / BEST."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v3_evidence_gate import EvidenceGateContractError  # noqa: E402
from hyperlexical.classification_v3_stage_b import (  # noqa: E402
    STAGE_B_RULE,
    calibrate_stage_b_thresholds,
    compose_end_to_end,
    evaluate_end_to_end,
    gold_end_to_end,
    next_action_for_stage_b,
    reserve_authorization,
    stage_b_contract,
)
import pytest  # noqa: E402


def test_stage_b_contract_and_gold_mapping():
    contract = stage_b_contract()
    assert contract["rule"] == STAGE_B_RULE
    assert contract["retrieval_only_on"] == "EVIDENCE_PRESENT"
    assert contract["train"] is False
    assert contract["v3_reserve"] is None
    assert gold_end_to_end(
        {"evidence_subtype": "POSITIVE_EVIDENCE", "candidate_families": ["ai-native"]}
    ) == {"decision_type": "FAMILY", "family": "ai-native"}
    assert gold_end_to_end({"evidence_subtype": "GENERIC_NONE"})["decision_type"] == "NONE"
    assert gold_end_to_end({"evidence_subtype": "AMBIGUOUS_EVIDENCE"})[
        "decision_type"
    ] == "ABSTAIN"


def test_retrieval_only_on_evidence_present():
    none = compose_end_to_end(
        evidence_decision="NO_EVIDENCE",
        ranked_candidates=[{"family": "ai-native", "score": 0.99}],
        family_score_min=0.5,
        family_margin_min=0.01,
    )
    assert none["decision_type"] == "NONE"
    uncertain = compose_end_to_end(
        evidence_decision="UNCERTAIN",
        ranked_candidates=[{"family": "ai-native", "score": 0.99}],
        family_score_min=0.5,
        family_margin_min=0.01,
    )
    assert uncertain["decision_type"] == "ABSTAIN"
    family = compose_end_to_end(
        evidence_decision="EVIDENCE_PRESENT",
        ranked_candidates=[
            {"family": "ai-native", "score": 0.9},
            {"family": "gaming-meta", "score": 0.1},
        ],
        family_score_min=0.5,
        family_margin_min=0.05,
    )
    assert family["decision_type"] == "FAMILY"
    assert family["family"] == "ai-native"


def test_end_to_end_metrics_and_authorization():
    rows = []
    # Gold NONE / Stage A NONE
    for i in range(40):
        rows.append(
            {
                "evidence_decision": "NO_EVIDENCE",
                "evidence_label": "NO_EVIDENCE",
                "gold_decision_type": "NONE",
                "gold_family": None,
                "top1_family": "ai-native",
                "top1_score": 0.9,
                "top2_family": "gaming-meta",
                "top2_score": 0.1,
            }
        )
    # One false entry
    rows.append(
        {
            "evidence_decision": "EVIDENCE_PRESENT",
            "evidence_label": "NO_EVIDENCE",
            "gold_decision_type": "NONE",
            "gold_family": None,
            "top1_family": "ai-native",
            "top1_score": 0.99,
            "top2_family": "gaming-meta",
            "top2_score": 0.1,
        }
    )
    # Gold FAMILY / Stage A PRESENT with clear margin
    for i in range(20):
        rows.append(
            {
                "evidence_decision": "EVIDENCE_PRESENT",
                "evidence_label": "EVIDENCE_PRESENT",
                "gold_decision_type": "FAMILY",
                "gold_family": "ai-native",
                "top1_family": "ai-native",
                "top1_score": 0.92,
                "top2_family": "gaming-meta",
                "top2_score": 0.2,
            }
        )
    metrics = evaluate_end_to_end(rows, family_score_min=0.5, family_margin_min=0.05)
    assert metrics["primary_gate_pass"] is True
    assert metrics["false_evidence_entry_rate_on_none"] == pytest.approx(1 / 41)
    # False Stage-A entry emits one wrong FAMILY; precision still above 0.80.
    assert metrics["family_emission_precision"] == pytest.approx(20 / 21)
    assert metrics["secondary_gate_pass"] is True
    auth = reserve_authorization(metrics)
    assert auth["decision"] == "RESERVE_SEAL_AUTHORIZED"
    assert auth["v3_reserve_created"] is False
    assert next_action_for_stage_b(auth).startswith("AUTHORIZE_SEAL_NEW_V3_RESERVE")


def test_calibration_respects_primary_gate():
    rows = []
    for i in range(30):
        rows.append(
            {
                "evidence_decision": "NO_EVIDENCE",
                "evidence_label": "NO_EVIDENCE",
                "gold_decision_type": "NONE",
                "gold_family": None,
                "top1_family": "ai-native",
                "top1_score": 0.2,
                "top2_family": "gaming-meta",
                "top2_score": 0.1,
            }
        )
    for i in range(20):
        rows.append(
            {
                "evidence_decision": "EVIDENCE_PRESENT",
                "evidence_label": "EVIDENCE_PRESENT",
                "gold_decision_type": "FAMILY",
                "gold_family": "ai-native",
                "top1_family": "ai-native",
                "top1_score": 0.9,
                "top2_family": "gaming-meta",
                "top2_score": 0.2,
            }
        )
    calibration = calibrate_stage_b_thresholds(rows)
    assert calibration["primary_gate_pass"] is True
    assert calibration["feasible"] is True
    assert calibration["family_emission_precision"] >= 0.80
