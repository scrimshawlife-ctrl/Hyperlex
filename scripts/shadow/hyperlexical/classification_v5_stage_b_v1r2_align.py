"""ALIGN_V5_STAGE_B_TO_V1R2 — Stage-B index/eval under canonical Stage-A + V1R2.

Builds a new Stage-B index on the identifiability-filtered V1R2 surface using
canonical factorized STAGE_A_BEST embeddings. Does not retrain Stage-A, does
not score spent reserve, does not mutate MODEL_WIDE_BEST. Historical V1R9
index remains retained.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import (
    CANONICAL_ID,
    KNOWN_LIMITATIONS,
    MODEL_WIDE_BEST_SHA256,
    PROMOTION_RECEIPT_SHA256,
    STAGE_A_BEST_SHA256,
    V5_STAGE_A_STATE,
)
from .classification_v5_stage_a_gold_identifiability_filter import (
    SURFACE_ID as V1R2_SURFACE_ID,
    V1R2_DATASET_SHA256_PIN,
)
from .classification_v5_stage_b import (
    HISTORICAL_V1R9_INDEX_SHA256,
    HISTORICAL_V1R9_MINIMUM_FAMILY_SCORE,
    HISTORICAL_V1R9_MINIMUM_TOP1_TOP2_MARGIN,
    STAGE_B_RULE,
)

ALIGN_RULE = "ALIGN_V5_STAGE_B_TO_V1R2"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V5-STAGE-B-V1R2-001"
SCHEMA_ALIGN = "hyperlex.classification.v5.stage_b_v1r2_alignment.v1"
NEXT_ACTION_ON_PASS = "SEAL_V5_STAGE_A_B_V1R2_PIPELINE_OR_SCOPED_PACKAGING"
NEXT_ACTION_ON_FAIL = "DIAGNOSE_V5_STAGE_B_V1R2_BEFORE_PACKAGING"

FALSE_ENTRY_MAX = 0.05
FAMILY_PRECISION_MIN = 0.80


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def alignment_contract() -> dict[str, Any]:
    return {
        "ALIGN_RULE": ALIGN_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "STAGE_A_CANONICAL": CANONICAL_ID,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "V5_STAGE_A_STATE": V5_STAGE_A_STATE,
        "surface_id": V1R2_SURFACE_ID,
        "surface_dataset_sha256": V1R2_DATASET_SHA256_PIN,
        "historical_v1r9_index_sha256": HISTORICAL_V1R9_INDEX_SHA256,
        "historical_v1r9_index_status": "RETAINED_HISTORICAL",
        "parent_promotion_receipt_sha256": PROMOTION_RECEIPT_SHA256,
        "rebuild_index": True,
        "rebuild_scope": "V1R2_UNDER_CANONICAL_STAGE_A_ONLY",
        "retune_floors": True,
        "retune_scope": "V1R2_VALIDATION_ONLY",
        "reserve_scored": False,
        "train_stage_a": False,
        "stage_b_rule": STAGE_B_RULE,
        "gates": {
            "false_evidence_entry_rate_on_none_max": FALSE_ENTRY_MAX,
            "family_emission_precision_min": FAMILY_PRECISION_MIN,
        },
        "known_limitations": dict(KNOWN_LIMITATIONS),
        "schema": SCHEMA_ALIGN,
    }


def choose_alignment_state(
    *,
    primary_gate_pass: bool,
    secondary_gate_pass: bool,
    index_sha256: str,
    stage_a_best: str,
) -> dict[str, Any]:
    ok = (
        primary_gate_pass
        and secondary_gate_pass
        and stage_a_best == STAGE_A_BEST_SHA256
        and bool(index_sha256)
        and index_sha256 != HISTORICAL_V1R9_INDEX_SHA256
    )
    return {
        "STAGE_B_V1R2_ALIGNMENT": "APPLIED" if ok else "ALIGNMENT_FAILED",
        "applied": ok,
        "active_stage_b_surface": V1R2_SURFACE_ID if ok else None,
        "reason": "ok" if ok else "gates_or_pins_failed",
    }


def build_alignment_receipt(
    *,
    metrics: Mapping[str, Any],
    calibration: Mapping[str, Any],
    index_sha256: str,
    code_revision: str,
    n_index_records: int,
    n_validation: int,
    aligned_at: str | None = None,
) -> dict[str, Any]:
    primary = bool(metrics.get("primary_gate_pass"))
    secondary = bool(metrics.get("secondary_gate_pass"))
    state = choose_alignment_state(
        primary_gate_pass=primary,
        secondary_gate_pass=secondary,
        index_sha256=index_sha256,
        stage_a_best=STAGE_A_BEST_SHA256,
    )
    payload = {
        "ALIGN_RULE": ALIGN_RULE,
        "BEST_MUTATED": False,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "NEXT_ACTION": (
            NEXT_ACTION_ON_PASS if state["applied"] else NEXT_ACTION_ON_FAIL
        ),
        "RESERVE_CONSUMED": False,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "STAGE_A_CANONICAL": CANONICAL_ID,
        "TRAIN": False,
        "V5_STAGE_A_STATE": V5_STAGE_A_STATE,
        "aligned_at": aligned_at or utc_now_iso(),
        "calibration": dict(calibration),
        "code_revision": code_revision,
        "contract": alignment_contract(),
        "historical_v1r9_index_sha256": HISTORICAL_V1R9_INDEX_SHA256,
        "index_sha256": index_sha256,
        "known_limitations": dict(KNOWN_LIMITATIONS),
        "metrics": dict(metrics),
        "n_index_records": n_index_records,
        "n_validation": n_validation,
        "parent_stage_b_contract": {
            "STAGE_A_BEST": STAGE_A_BEST_SHA256,
            "frozen_index_sha256": HISTORICAL_V1R9_INDEX_SHA256,
            "minimum_family_score": HISTORICAL_V1R9_MINIMUM_FAMILY_SCORE,
            "minimum_top1_top2_margin": HISTORICAL_V1R9_MINIMUM_TOP1_TOP2_MARGIN,
            "status": "SUPERSEDED_IF_ALIGNMENT_APPLIED"
            if state["applied"]
            else "REMAINS_ACTIVE_PENDING_ALIGNMENT",
        },
        "schema": SCHEMA_ALIGN,
        "state": state,
        "surface_dataset_sha256": V1R2_DATASET_SHA256_PIN,
        "surface_id": V1R2_SURFACE_ID,
    }
    payload["STAGE_B_V1R2_ALIGNMENT_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in payload.items()
                if k != "STAGE_B_V1R2_ALIGNMENT_RECEIPT_SHA256"
            }
        )
    )
    return payload


def active_stage_b_v1r2_contract(
    *,
    index_sha256: str,
    minimum_family_score: float,
    minimum_top1_top2_margin: float,
) -> dict[str, Any]:
    """Active Stage-B binding after successful V1R2 alignment."""
    return {
        "BEST": "UNCHANGED",
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "STAGE_A_CANONICAL": CANONICAL_ID,
        "dataset_sha256": V1R2_DATASET_SHA256_PIN,
        "entry_invariant": {
            "EVIDENCE_PRESENT": "PERMIT_STAGE_B",
            "NO_EVIDENCE": "STOP",
            "UNCERTAIN": "ABSTAIN",
            "rule": "Stage B may execute only when Stage A == EVIDENCE_PRESENT",
        },
        "experiment_id": EXPERIMENT_ID,
        "floors_retuned": True,
        "frozen_index_sha256": index_sha256,
        "historical_v1r9_index_sha256": HISTORICAL_V1R9_INDEX_SHA256,
        "index_rebuilt": True,
        "minimum_family_score": float(minimum_family_score),
        "minimum_top1_top2_margin": float(minimum_top1_top2_margin),
        "parent_promotion_receipt_sha256": PROMOTION_RECEIPT_SHA256,
        "retrieval_only_on": "EVIDENCE_PRESENT",
        "rule": STAGE_B_RULE,
        "schema": "hyperlex.classification.v5.stage_b_integration.v1r2",
        "surface_id": V1R2_SURFACE_ID,
        "train": False,
        "v5_reserve": None,
    }
