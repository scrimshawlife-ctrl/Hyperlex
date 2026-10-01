"""EVALUATE_FULL_V5_PIPELINE — read-only Stage-A→B evaluation under frozen pins.

Evaluates under canonical Stage-A + active V1R2-aligned Stage-B pins.
Does not train Stage-A, score spent reserve, or mutate BEST / STAGE_A_BEST.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_b_pipeline import (
    PIPELINE_ID,
    pipeline_contract,
    verify_entry_gating,
)
from .classification_v5_stage_a_canonical import (
    CANONICAL_ID,
    KNOWN_LIMITATIONS,
    MODEL_WIDE_BEST_SHA256,
    STAGE_A_BEST_SHA256,
    V5_STAGE_A_STATE,
)
from .classification_v5_stage_b import (
    EXPERIMENT_ID as STAGE_B_EXPERIMENT_ID,
    FROZEN_INDEX_SHA256,
    FROZEN_MINIMUM_FAMILY_SCORE,
    FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
    INDEX_REBUILT,
    FLOORS_RETUNED,
    STAGE_B_RULE,
    evaluate_end_to_end,
    stage_b_contract,
)

EVAL_RULE = "EVALUATE_FULL_V5_PIPELINE"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V5-PIPELINE-EVAL-001"
SCHEMA_EVAL = "hyperlex.classification.v5.pipeline_evaluation.v1"
NEXT_ACTION_ON_PASS = "AUTHORIZE_V5_PRODUCTION_PACKAGING_OR_OPERATOR_HUB_GATE"

# V1R2 Stage-B index embeddings were built under canonical factorized STAGE_A_BEST.
INDEX_EMBEDDING_PARENT_STAGE_A = STAGE_A_BEST_SHA256


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def evaluate_pipeline_rows(
    score_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Score frozen floors on precomputed Stage-A decisions + retrieval tops."""
    metrics = evaluate_end_to_end(
        list(score_rows),
        family_score_min=FROZEN_MINIMUM_FAMILY_SCORE,
        family_margin_min=FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
    )
    entry = verify_entry_gating()
    none_entered = sum(
        1
        for row in score_rows
        if row.get("evidence_decision") == "NO_EVIDENCE"
        and row.get("invoked_stage_b") is True
    )
    uncertain_entered = sum(
        1
        for row in score_rows
        if row.get("evidence_decision") == "UNCERTAIN"
        and row.get("invoked_stage_b") is True
    )
    present_blocked = sum(
        1
        for row in score_rows
        if row.get("evidence_decision") == "EVIDENCE_PRESENT"
        and row.get("invoked_stage_b") is False
    )
    gating = {
        "none_entered_stage_b": none_entered,
        "uncertain_entered_stage_b": uncertain_entered,
        "present_blocked_from_stage_b": present_blocked,
        "entry_contract_pass": entry["pass"],
        "pass": none_entered == 0
        and uncertain_entered == 0
        and present_blocked == 0
        and entry["pass"],
    }
    decision_counts = {
        "NO_EVIDENCE": sum(
            1 for r in score_rows if r.get("evidence_decision") == "NO_EVIDENCE"
        ),
        "EVIDENCE_PRESENT": sum(
            1 for r in score_rows if r.get("evidence_decision") == "EVIDENCE_PRESENT"
        ),
        "UNCERTAIN": sum(
            1 for r in score_rows if r.get("evidence_decision") == "UNCERTAIN"
        ),
    }
    return {
        "metrics": metrics,
        "gating": gating,
        "decision_counts": decision_counts,
        "n": len(score_rows),
        "floors": {
            "minimum_family_score": FROZEN_MINIMUM_FAMILY_SCORE,
            "minimum_top1_top2_margin": FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
            "floors_retuned": FLOORS_RETUNED,
        },
        "pass": bool(gating["pass"] and metrics.get("primary_gate_pass")),
    }


def packaging_limitations() -> dict[str, Any]:
    return {
        **KNOWN_LIMITATIONS,
        "INDEX_ENCODER_PARENT": (
            "Stage-B V1R2 index embeddings sealed under canonical STAGE_A_BEST "
            f"{INDEX_EMBEDDING_PARENT_STAGE_A[:16]}…; queries encode under the "
            "same checkpoint."
        ),
        "RESERVE": "SPENT_NOT_RESCORED",
        "HUB_PUBLISH": "NOT_AUTHORIZED",
    }


def build_evaluation_receipt(
    *,
    evaluation: Mapping[str, Any],
    code_revision: str,
    surface_dataset_sha256: str,
    index_sha256: str,
    evaluated_at: str | None = None,
) -> dict[str, Any]:
    contract = stage_b_contract()
    payload = {
        "BEST_MUTATED": False,
        "CANONICAL_ID": CANONICAL_ID,
        "EVAL_RULE": EVAL_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "NEXT_ACTION": (
            NEXT_ACTION_ON_PASS
            if evaluation.get("pass")
            else "DIAGNOSE_V5_PIPELINE_BEFORE_PACKAGING"
        ),
        "PIPELINE_ID": PIPELINE_ID,
        "RESERVE_CONSUMED": False,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "STAGE_B_EXPERIMENT_ID": STAGE_B_EXPERIMENT_ID,
        "STAGE_B_RULE": STAGE_B_RULE,
        "TRAIN": False,
        "V5_STAGE_A_STATE": V5_STAGE_A_STATE,
        "code_revision": code_revision,
        "evaluated_at": evaluated_at or utc_now_iso(),
        "evaluation": dict(evaluation),
        "frozen_index_sha256": FROZEN_INDEX_SHA256,
        "index_embedding_parent_stage_a": INDEX_EMBEDDING_PARENT_STAGE_A,
        "index_rebuilt": INDEX_REBUILT,
        "index_sha256_observed": index_sha256,
        "known_limitations": packaging_limitations(),
        "pipeline_contract": pipeline_contract(),
        "schema": SCHEMA_EVAL,
        "stage_b_contract": contract,
        "surface_dataset_sha256": surface_dataset_sha256,
    }
    checks = {
        "index_pin_match": index_sha256 == FROZEN_INDEX_SHA256,
        "stage_a_parent_match": contract.get("STAGE_A_BEST") == STAGE_A_BEST_SHA256,
        "evaluation_pass": bool(evaluation.get("pass")),
    }
    payload["checks"] = checks
    payload["PIPELINE_EVAL_PASS"] = all(checks.values())
    if not payload["PIPELINE_EVAL_PASS"]:
        payload["NEXT_ACTION"] = "DIAGNOSE_V5_PIPELINE_BEFORE_PACKAGING"
    payload["PIPELINE_EVAL_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in payload.items()
                if k != "PIPELINE_EVAL_RECEIPT_SHA256"
            }
        )
    )
    return payload
