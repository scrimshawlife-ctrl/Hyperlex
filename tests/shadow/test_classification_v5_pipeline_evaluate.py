"""Tests for full V5 pipeline evaluation + production packaging contracts."""

from __future__ import annotations

from hyperlexical.classification_v5_pipeline_evaluate import (
    EVAL_RULE,
    FROZEN_INDEX_SHA256,
    STAGE_A_BEST_SHA256,
    build_evaluation_receipt,
    evaluate_pipeline_rows,
)
from hyperlexical.classification_v5_production_packaging import (
    HUB_STATUS,
    PACKAGING_ID,
    build_packaging_receipt,
    packaging_contract,
)
from hyperlexical.classification_v5_stage_b import (
    FROZEN_MINIMUM_FAMILY_SCORE,
    FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
)


def _row(
    decision: str,
    *,
    gold_type: str = "NONE",
    gold_family=None,
    top1="memetic",
    top1_score=0.9,
    top2="gaming-meta",
    top2_score=0.1,
    invoked=None,
):
    return {
        "evidence_decision": decision,
        "evidence_label": decision if decision != "UNCERTAIN" else "UNCERTAIN",
        "evidence_subtype": "ORDINARY_DOMAIN_NONE",
        "gold_decision_type": gold_type,
        "gold_family": gold_family,
        "invoked_stage_b": (
            (decision == "EVIDENCE_PRESENT") if invoked is None else invoked
        ),
        "top1_family": top1,
        "top1_score": top1_score,
        "top2_family": top2,
        "top2_score": top2_score,
        "top3_family": None,
        "top3_score": None,
    }


def test_evaluate_gating_and_floors():
    assert EVAL_RULE == "EVALUATE_FULL_V5_PIPELINE"
    assert STAGE_A_BEST_SHA256.startswith("f2b00c5d")
    rows = [
        _row("NO_EVIDENCE"),
        _row("UNCERTAIN"),
        _row(
            "EVIDENCE_PRESENT",
            gold_type="FAMILY",
            gold_family="memetic",
            top1_score=0.9,
            top2_score=0.1,
        ),
    ]
    out = evaluate_pipeline_rows(rows)
    assert out["gating"]["pass"] is True
    assert out["floors"]["minimum_family_score"] == FROZEN_MINIMUM_FAMILY_SCORE
    assert out["floors"]["minimum_top1_top2_margin"] == FROZEN_MINIMUM_TOP1_TOP2_MARGIN
    bad = evaluate_pipeline_rows(
        [_row("NO_EVIDENCE", invoked=True)]
    )
    assert bad["gating"]["pass"] is False


def test_receipts_and_packaging():
    rows = [_row("NO_EVIDENCE"), _row("EVIDENCE_PRESENT", gold_type="FAMILY", gold_family="memetic")]
    evaluation = evaluate_pipeline_rows(rows)
    receipt = build_evaluation_receipt(
        evaluation=evaluation,
        code_revision="deadbeef",
        surface_dataset_sha256="a" * 64,
        index_sha256=FROZEN_INDEX_SHA256,
        evaluated_at="2026-10-01T00:00:00Z",
    )
    assert "PIPELINE_EVAL_RECEIPT_SHA256" in receipt
    assert receipt["index_rebuilt"] is False
    assert receipt["RESERVE_CONSUMED"] is False
    pack = build_packaging_receipt(
        code_revision="deadbeef",
        pipeline_eval_receipt_sha256=receipt["PIPELINE_EVAL_RECEIPT_SHA256"],
        pipeline_eval_pass=True,
        sealed_at="2026-10-01T00:00:00Z",
    )
    assert pack["PACKAGING_ID"] == PACKAGING_ID
    assert pack["HUB_STATUS"] == HUB_STATUS
    assert packaging_contract()["publish_authorized"] is False
