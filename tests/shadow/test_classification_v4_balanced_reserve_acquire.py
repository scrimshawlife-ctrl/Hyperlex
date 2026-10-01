"""v4 balanced reserve acquire contracts. No GPU / BEST move / network."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v4_balanced_reserve_acquire import (  # noqa: E402
    ACQUIRE_RULE,
    BALANCE_FLOORS,
    SPENT_V3_ROWS_SHA,
    acquire_contract,
    assemble_acquire_receipt,
    audit_balance,
    build_acquire_row,
    decide_acquire_disposition,
    family_for_sense_labels,
    next_action_for_acquire_disposition,
    validate_acquire_disjointness,
)
from hyperlexical.holdout_guard import normalized_text_sha256  # noqa: E402


def test_contract_pins_spent_reserves_and_floors():
    contract = acquire_contract()
    assert contract["rule"] == ACQUIRE_RULE
    assert contract["spent_v2_reserve_reuse"] is False
    assert contract["spent_v3_reserve_reuse"] is False
    assert contract["spent_v3_rows_sha256"] == SPENT_V3_ROWS_SHA
    assert contract["score_reserve"] is False
    assert contract["train"] is False
    assert contract["recalibrate"] is False
    assert contract["balance_floors"] == BALANCE_FLOORS
    assert contract["balance_floors"]["min_none"] >= 40
    assert contract["balance_floors"]["max_single_family_share_of_present"] <= 0.20


def test_sense_label_mapping_and_row_build():
    assert family_for_sense_labels(["Internet slang"])["family"] == "internet-slang"
    assert family_for_sense_labels(["honorific"])["family"] == "social-evaluation"
    assert family_for_sense_labels(["botany"])["status"] == "none"
    assert family_for_sense_labels(["internet slang", "meme"])["status"] == "ambiguous"
    present = build_acquire_row(
        {
            "text": "a viral image macro used online",
            "lineage": "memetic",
            "class": "OBSERVED",
            "revision_id": 1,
            "revision_sha1": "abc",
            "revision_timestamp": "2026-09-30T00:00:00Z",
            "source_url": "https://en.wiktionary.org/wiki/x",
            "title": "x",
        }
    )
    assert present["evidence_label"] == "EVIDENCE_PRESENT"
    assert present["gold_family"] == "memetic"
    none = build_acquire_row(
        {
            "text": "a flowering plant of the rose family",
            "lineage": "none",
            "class": "OBSERVED",
            "evidence_subtype": "HARD_NONE",
        }
    )
    assert none["evidence_label"] == "NO_EVIDENCE"
    assert none["gold_decision_type"] == "NONE"


def test_balance_and_disposition():
    rows = []
    for family_i, family in enumerate(
        [
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
    ):
        for j in range(7):
            rows.append(
                build_acquire_row(
                    {
                        "text": f"{family} acquire phrase {j} {family_i}",
                        "lineage": family,
                        "class": "OBSERVED",
                    }
                )
            )
    for j in range(48):
        rows.append(
            build_acquire_row(
                {
                    "text": f"ordinary botanical gloss {j}",
                    "lineage": "none",
                    "class": "OBSERVED",
                    "evidence_subtype": "HARD_NONE",
                }
            )
        )
    balance = audit_balance(rows)
    assert balance["balance_pass"] is True
    blocked = {rows[0]["identity"]: "spent_v3"}
    invalid = validate_acquire_disjointness(rows, blocked_ids=blocked)
    assert any(item.startswith("blocked_overlap:spent_v3:") for item in invalid)
    ready = decide_acquire_disposition(invalid_reasons=[], balance=balance)
    assert ready["disposition"] == "ACQUIRE_READY"
    assert next_action_for_acquire_disposition(ready).startswith("BALANCED_RESERVE")
    skewed = audit_balance(
        [
            build_acquire_row(
                {
                    "text": f"internet slang only {i}",
                    "lineage": "internet-slang",
                    "class": "OBSERVED",
                }
            )
            for i in range(100)
        ]
        + [
            build_acquire_row(
                {
                    "text": f"none only {i}",
                    "lineage": "none",
                    "class": "OBSERVED",
                    "evidence_subtype": "GENERIC_NONE",
                }
            )
            for i in range(8)
        ]
    )
    assert skewed["balance_pass"] is False
    fail = decide_acquire_disposition(invalid_reasons=[], balance=skewed)
    assert fail["disposition"] == "ACQUIRE_QUOTA_UNFILLED"
    body = "\n".join(
        __import__("json").dumps(row, sort_keys=True, separators=(",", ":"))
        for row in rows
    ) + "\n"
    receipt = assemble_acquire_receipt(
        {
            "balance": balance,
            "disposition": ready,
            "next_action": next_action_for_acquire_disposition(ready),
            "rows_sha256": normalized_text_sha256(body),
        }
    )
    assert receipt["receipt_sha256"]
    assert receipt["BEST"] == "UNCHANGED"
