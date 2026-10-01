"""Tests for V1R2 Stage-B alignment under canonical Stage-A."""

from __future__ import annotations

from hyperlexical.classification_v5_stage_a_canonical import STAGE_A_BEST_SHA256
from hyperlexical.classification_v5_stage_b import (
    FROZEN_INDEX_SHA256,
    HISTORICAL_V1R9_INDEX_SHA256,
)
from hyperlexical.classification_v5_stage_b_v1r2_align import (
    ALIGN_RULE,
    EXPERIMENT_ID,
    active_stage_b_v1r2_contract,
    alignment_contract,
    build_alignment_receipt,
    choose_alignment_state,
)


def test_alignment_pins_and_state():
    assert ALIGN_RULE == "ALIGN_V5_STAGE_B_TO_V1R2"
    assert EXPERIMENT_ID.endswith("STAGE-B-V1R2-001")
    contract = alignment_contract()
    assert contract["STAGE_A_BEST"] == STAGE_A_BEST_SHA256
    assert contract["surface_dataset_sha256"].startswith("492ed367")
    assert contract["historical_v1r9_index_sha256"] == HISTORICAL_V1R9_INDEX_SHA256
    assert HISTORICAL_V1R9_INDEX_SHA256.startswith("3fd6c87a")
    assert FROZEN_INDEX_SHA256.startswith("4febe96e")
    assert FROZEN_INDEX_SHA256 != HISTORICAL_V1R9_INDEX_SHA256
    assert contract["reserve_scored"] is False
    assert contract["train_stage_a"] is False
    ok = choose_alignment_state(
        primary_gate_pass=True,
        secondary_gate_pass=True,
        index_sha256="a" * 64,
        stage_a_best=STAGE_A_BEST_SHA256,
    )
    assert ok["applied"] is True
    bad = choose_alignment_state(
        primary_gate_pass=True,
        secondary_gate_pass=True,
        index_sha256=HISTORICAL_V1R9_INDEX_SHA256,
        stage_a_best=STAGE_A_BEST_SHA256,
    )
    assert bad["applied"] is False


def test_receipt_and_active_contract():
    receipt = build_alignment_receipt(
        metrics={
            "primary_gate_pass": True,
            "secondary_gate_pass": True,
            "false_evidence_entry_rate_on_none": 0.02,
            "family_emission_precision": 0.85,
        },
        calibration={
            "feasible": True,
            "minimum_family_score": 0.55,
            "minimum_top1_top2_margin": 0.05,
        },
        index_sha256="b" * 64,
        code_revision="deadbeef",
        n_index_records=900,
        n_validation=848,
        aligned_at="2026-10-01T00:00:00Z",
    )
    assert receipt["state"]["applied"] is True
    assert "STAGE_B_V1R2_ALIGNMENT_RECEIPT_SHA256" in receipt
    assert receipt["parent_stage_b_contract"]["frozen_index_sha256"] == (
        HISTORICAL_V1R9_INDEX_SHA256
    )
    active = active_stage_b_v1r2_contract(
        index_sha256="b" * 64,
        minimum_family_score=0.55,
        minimum_top1_top2_margin=0.05,
    )
    assert active["STAGE_A_BEST"].startswith("f2b00c5d")
    assert active["index_rebuilt"] is True
    assert active["dataset_sha256"].startswith("492ed367")
