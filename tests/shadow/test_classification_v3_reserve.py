"""v3 reserve seal/disposition tests. No GPU / BEST move."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v3_reserve import (  # noqa: E402
    RESERVE_RULE,
    build_reserve_row,
    collect_available_reserve_rows,
    decide_v3_reserve_disposition,
    next_action_for_v3_disposition,
    reserve_contract,
    seal_reserve_manifest,
    validate_reserve_disjointness,
)
from hyperlexical.holdout_guard import normalized_text_sha256  # noqa: E402


def test_reserve_contract_frozen():
    contract = reserve_contract()
    assert contract["rule"] == RESERVE_RULE
    assert contract["spent_v2_reserve_reuse"] is False
    assert contract["recalibrate"] is False
    assert contract["frozen_thresholds"]["none_threshold"] == 0.05
    assert contract["frozen_thresholds"]["minimum_family_score"] == 0.96


def test_collect_available_excludes_spent_and_surface():
    text_ok = "fresh reserve slang phrase"
    text_spent = "spent reserve phrase"
    text_surface = "surface phrase already used"
    ok_id = normalized_text_sha256(text_ok)
    spent_id = normalized_text_sha256(text_spent)
    surface_id = normalized_text_sha256(text_surface)
    ledger = {
        "identities": [
            {"normalized_text_sha256": ok_id, "state": "AVAILABLE"},
            {"normalized_text_sha256": spent_id, "state": "AVAILABLE"},
            {"normalized_text_sha256": surface_id, "state": "AVAILABLE"},
            {
                "normalized_text_sha256": normalized_text_sha256("consumed"),
                "state": "TRAIN_CONSUMED",
            },
        ]
    }
    hub = [
        {"text": text_ok, "lineage": "internet-slang", "class": "OBSERVED", "task": "classify"},
        {"text": text_spent, "lineage": "none", "class": "OBSERVED", "task": "classify"},
        {"text": text_surface, "lineage": "memetic", "class": "OBSERVED", "task": "classify"},
        {
            "text": "consumed",
            "lineage": "ai-native",
            "class": "OBSERVED",
            "task": "classify",
        },
    ]
    collected = collect_available_reserve_rows(
        ledger=ledger,
        hub_rows=hub,
        surface_ids={surface_id},
        spent_v2_ids={spent_id},
    )
    assert collected["n"] == 1
    assert collected["rows"][0]["identity"] == ok_id
    sealed = seal_reserve_manifest(collected["rows"])
    assert sealed["manifest"]["n"] == 1
    reasons = validate_reserve_disjointness(
        collected["rows"],
        surface_ids={surface_id},
        spent_v2_ids={spent_id},
        index_ids=set(),
    )
    assert reasons == []


def test_disposition_pass_fail_invalid():
    invalid = decide_v3_reserve_disposition(
        invalid_reasons=["surface_overlap:1"], metrics={}
    )
    assert invalid["disposition"] == "RESERVE_INVALID"
    fail = decide_v3_reserve_disposition(
        invalid_reasons=[],
        metrics={
            "primary_gate_pass": True,
            "secondary_gate_pass": False,
            "false_evidence_entry_rate_on_none": 0.01,
            "family_emission_precision": 0.5,
        },
    )
    assert fail["disposition"] == "RESERVE_FAIL"
    assert next_action_for_v3_disposition(fail).startswith("STOP")
    passed = decide_v3_reserve_disposition(
        invalid_reasons=[],
        metrics={
            "primary_gate_pass": True,
            "secondary_gate_pass": True,
            "false_evidence_entry_rate_on_none": 0.01,
            "family_emission_precision": 0.85,
        },
    )
    assert passed["disposition"] == "RESERVE_PASS"
    row = build_reserve_row(
        {"text": "ai native slang", "lineage": "ai-native", "class": "OBSERVED"}
    )
    assert row["evidence_label"] == "EVIDENCE_PRESENT"
    assert row["gold_family"] == "ai-native"
