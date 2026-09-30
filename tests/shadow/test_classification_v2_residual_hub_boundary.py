"""Residual hub boundary pass tests. No train / reserve / BEST / SE-RD merge."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v2_ontology_merge_pair import (  # noqa: E402
    KEEP_FAMILY,
    MERGED_LABEL,
)
from hyperlexical.classification_v2_residual_hub_boundary import (  # noqa: E402
    HUB_FAMILIES,
    HUB_RULE,
    RESIDUAL_REVIEW_SHA,
    assemble_hub_pass,
    classify_hub_row,
    enforce_support_floors,
    hub_contract,
    overlap_reduction,
    training_gate_hub,
)


def test_contract_keeps_se_rd_and_forbids_train():
    contract = hub_contract()
    assert contract["rule"] == HUB_RULE
    assert contract["train"] is False
    assert contract["moves_best"] is False
    assert contract["reserve_scored"] is False
    assert contract["keeps_se_rd_separate"] is True
    assert contract["applies_ontology_change"] is False
    assert contract["residual_review_sha256"] == RESIDUAL_REVIEW_SHA
    assert list(contract["hub_families"]) == list(HUB_FAMILIES)
    assert MERGED_LABEL in HUB_FAMILIES
    assert KEEP_FAMILY not in HUB_FAMILIES


def test_classify_hub_zero_core_and_competitor_dominant():
    drop = classify_hub_row(
        family="internet-slang",
        text="A vague generic system without domain cues",
        identity="a" * 64,
        hub_competitors={"internet-slang": ["spiritual-mystic", MERGED_LABEL]},
    )
    assert drop["decision"] == "DROP"
    assert "hub_zero_core_hits" in drop["reasons"]

    dominant = classify_hub_row(
        family="music-entertainment",
        text="occult mystic spiritual ritual pagan ceremony",
        identity="b" * 64,
        hub_competitors={"music-entertainment": ["spiritual-mystic"]},
    )
    assert dominant["decision"] == "DROP"
    assert any(reason.startswith("competitor_dominant:") for reason in dominant["reasons"])

    keep = classify_hub_row(
        family="music-entertainment",
        text="A music song melody album concert performance",
        identity="c" * 64,
        hub_competitors={"music-entertainment": ["spiritual-mystic"]},
    )
    assert keep["decision"] == "KEEP"


def test_support_floor_rescue_and_gate():
    rows = [
        {
            "decision": "DROP",
            "family": "internet-slang",
            "identity": f"{index:064d}",
            "own_core_hits": 0,
            "reasons": ["hub_zero_core_hits"],
            "text": "x",
        }
        for index in range(13)
    ]
    rescued = enforce_support_floors(rows, vocabulary=["internet-slang"])
    assert sum(1 for row in rescued if row["decision"] == "KEEP") == 12
    reduction = overlap_reduction(
        {
            "high_overlap_pair_count": 34,
            "largest_collapse_component": 12,
            "threshold": 0.8,
        },
        {
            "high_overlap_pair_count": 20,
            "largest_collapse_component": 9,
            "threshold": 0.8,
        },
    )
    assert reduction["percentage_reduction"] > 0.3
    vocab = ["internet-slang", "memetic", "betting-sharp", MERGED_LABEL]
    support = {family: 12 for family in vocab}
    gate = training_gate_hub(reduction=reduction, support_post=support, vocabulary=vocab)
    assert gate["training_gate"] == "OPEN"


def test_assemble_hub_pass():
    artifact = assemble_hub_pass(
        {
            "classifications": [
                {
                    "decision": "KEEP",
                    "family": MERGED_LABEL,
                    "identity": "d" * 64,
                    "own_core_hits": 2,
                    "reasons": [],
                    "text": "status",
                }
            ],
            "hub_competitors": {MERGED_LABEL: [KEEP_FAMILY]},
            "overlap_pre": {
                "collapse_high_overlap_pairs": 30,
                "high_overlap_pair_count": 34,
                "largest_collapse_component": 12,
                "threshold": 0.8,
            },
            "overlap_post": {
                "collapse_high_overlap_pairs": 20,
                "high_overlap_pair_count": 22,
                "largest_collapse_component": 10,
                "threshold": 0.8,
            },
            "overlap_reduction": {
                "absolute_reduction": 12,
                "percentage_reduction": 12 / 34,
                "largest_collapse_component_pre": 12,
                "largest_collapse_component_post": 10,
            },
            "support_pre": {MERGED_LABEL: 12},
            "support_post": {MERGED_LABEL: 10},
            "training_gate": {
                "training_gate": "CLOSED",
                "residual_blockers": ["MATERIAL_OVERLAP_REDUCTION_NOT_MET"],
                "next_action": "RESOLVE_RESIDUAL_BLOCKERS",
            },
            "export_path": "/tmp/x.jsonl",
            "export_sha256": "e" * 64,
        }
    )
    assert artifact["hub_pass_state"] == "SEALED"
    assert artifact["relationship_dating_merged"] is False
    assert artifact["keeps_se_rd_separate"] is True
    assert artifact["artifact_sha256"]
    assert artifact["train"] is False
