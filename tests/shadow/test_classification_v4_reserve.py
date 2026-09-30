"""v4 balanced reserve seal/disposition tests. No GPU / BEST move."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v4_balanced_reserve_acquire import (  # noqa: E402
    ACQUIRE_RULE,
    build_acquire_row,
)
from hyperlexical.classification_v4_reserve import (  # noqa: E402
    ACQUIRE_ROWS_SHA,
    RESERVE_RULE,
    assemble_reserve_eval_receipt,
    decide_v4_reserve_disposition,
    next_action_for_v4_disposition,
    reserve_contract,
    seal_reserve_from_acquire,
    validate_v4_reserve_disjointness,
)


def _balanced_rows() -> list[dict]:
    rows = []
    families = [
        "ai-native",
        "betting-sharp",
        "crypto-degen",
        "gaming-meta",
        "internet-slang",
        "memetic",
        "social-evaluation",
        "relationship-dating",
        "conflict-aggression",
        "technology-ai",
        "workplace-career",
        "sports-competition",
    ]
    for family_i, family in enumerate(families):
        for j in range(7):
            rows.append(
                build_acquire_row(
                    {
                        "text": f"{family} v4 reserve phrase {j} {family_i}",
                        "lineage": family,
                        "class": "OBSERVED",
                    }
                )
            )
    for j in range(48):
        rows.append(
            build_acquire_row(
                {
                    "text": f"ordinary botanical gloss v4 {j}",
                    "lineage": "none",
                    "class": "OBSERVED",
                    "evidence_subtype": "HARD_NONE",
                }
            )
        )
    return rows


def test_v4_reserve_contract_frozen():
    contract = reserve_contract()
    assert contract["rule"] == RESERVE_RULE
    assert contract["acquire_rule"] == ACQUIRE_RULE
    assert contract["acquire_rows_sha256"] == ACQUIRE_ROWS_SHA
    assert contract["spent_v2_reserve_reuse"] is False
    assert contract["spent_v3_reserve_reuse"] is False
    assert contract["recalibrate"] is False
    assert contract["train"] is False
    assert contract["frozen_thresholds"]["none_threshold"] == 0.05
    assert contract["frozen_thresholds"]["minimum_family_score"] == 0.96


def test_seal_and_disjointness():
    rows = _balanced_rows()
    sealed = seal_reserve_from_acquire(rows)
    assert sealed["manifest"]["n"] == len(rows)
    assert sealed["manifest"]["balance"]["balance_pass"] is True
    assert sealed["manifest"]["rows_sha256"]
    spent_id = rows[0]["identity"]
    reasons = validate_v4_reserve_disjointness(
        rows,
        surface_ids=set(),
        spent_v2_ids=set(),
        spent_v3_ids={spent_id},
        index_ids=set(),
    )
    assert any(item.startswith("spent_v3_overlap:") for item in reasons)


def test_disposition_and_receipt():
    fail = decide_v4_reserve_disposition(
        invalid_reasons=[],
        metrics={
            "primary_gate_pass": False,
            "secondary_gate_pass": False,
            "false_evidence_entry_rate_on_none": 0.2,
            "family_emission_precision": 0.0,
        },
    )
    assert fail["disposition"] == "RESERVE_FAIL"
    assert next_action_for_v4_disposition(fail).startswith("STOP")
    passed = decide_v4_reserve_disposition(
        invalid_reasons=[],
        metrics={
            "primary_gate_pass": True,
            "secondary_gate_pass": True,
            "false_evidence_entry_rate_on_none": 0.01,
            "family_emission_precision": 0.85,
        },
    )
    assert passed["disposition"] == "RESERVE_PASS"
    receipt = assemble_reserve_eval_receipt(
        {
            "disposition": passed,
            "metrics": {
                "n": 10,
                "primary_gate_pass": True,
                "secondary_gate_pass": True,
            },
            "next_action": next_action_for_v4_disposition(passed),
            "reserve_manifest_sha256": "a" * 64,
            "reserve_rows_sha256": "b" * 64,
            "validation_reference": {"family_emission_precision": 0.815},
        }
    )
    assert receipt["receipt_sha256"]
    assert receipt["BEST"] == "UNCHANGED"
    assert receipt["audit_state"]["reserve_scored_once"] is True
