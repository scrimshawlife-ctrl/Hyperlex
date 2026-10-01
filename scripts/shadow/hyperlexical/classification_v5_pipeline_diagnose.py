"""DIAGNOSE_V5_PIPELINE_BEFORE_PACKAGING — surface/index alignment diagnosis.

Read-only. Does not retrain, rebuild index, retune floors, or score reserve.
"""

from __future__ import annotations

from typing import Any, Mapping

from .classification_v5_pipeline_evaluate import (
    FROZEN_INDEX_SHA256,
    INDEX_EMBEDDING_PARENT_STAGE_A,
)
from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import (
    CANONICAL_ID,
    STAGE_A_BEST_SHA256,
)
from .classification_v5_stage_a_gold_identifiability_filter import (
    SURFACE_ID as V1R2_SURFACE_ID,
    V1R2_DATASET_SHA256_PIN,
)
from .classification_v5_stage_a_two_stage import AUTHORIZED_DATASET_SHA as V1R9_DATASET_SHA

DIAGNOSE_RULE = "DIAGNOSE_V5_PIPELINE_BEFORE_PACKAGING"
SCHEMA_DIAGNOSE = "hyperlex.classification.v5.pipeline_diagnosis.v1"
PRIMARY_DIAGNOSIS = "STAGE_A_V1R2_CANONICAL_ON_STAGE_B_V1R9_SURFACE"
NEXT_ACTION = "ALIGN_V5_STAGE_B_TO_V1R2_OR_SCOPED_CROSS_SURFACE_EVAL"

V1R9_SURFACE_ID = "HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R9"


def diagnose_pipeline_eval(eval_receipt: Mapping[str, Any]) -> dict[str, Any]:
    metrics = (eval_receipt.get("evaluation") or {}).get("metrics") or {}
    gating = (eval_receipt.get("evaluation") or {}).get("gating") or {}
    false_entry = float(metrics.get("false_evidence_entry_rate_on_none") or -1.0)
    findings = {
        "entry_gating_intact": bool(gating.get("pass")),
        "stage_a_canonical_surface": V1R2_SURFACE_ID,
        "stage_a_canonical_dataset_sha256": V1R2_DATASET_SHA256_PIN,
        "stage_b_eval_surface": V1R9_SURFACE_ID,
        "stage_b_eval_dataset_sha256": V1R9_DATASET_SHA,
        "stage_b_index_sha256": FROZEN_INDEX_SHA256,
        "index_embedding_parent_stage_a": INDEX_EMBEDDING_PARENT_STAGE_A,
        "query_encoder_stage_a": STAGE_A_BEST_SHA256,
        "false_entry_on_v1r9": false_entry,
        "false_entry_gate": 0.05,
        "primary_gate_pass": bool(metrics.get("primary_gate_pass")),
        "family_emission_precision": metrics.get("family_emission_precision"),
        "surface_mismatch": V1R2_DATASET_SHA256_PIN != V1R9_DATASET_SHA,
        "index_encoder_parent_mismatch": (
            INDEX_EMBEDDING_PARENT_STAGE_A != STAGE_A_BEST_SHA256
        ),
    }
    root_causes = [
        {
            "id": "SURFACE_MISMATCH",
            "detail": (
                "Canonical Stage-A was settled on identifiability-filtered V1R2; "
                "frozen Stage-B index/validation surface remains V1R9."
            ),
        },
        {
            "id": "INDEX_ENCODER_PARENT_MISMATCH",
            "detail": (
                "Index embeddings sealed under superseded two-stage STAGE_A_BEST; "
                "queries encode under factorized canonical STAGE_A_BEST. "
                "Index rebuild forbidden by freeze contract."
            ),
        },
    ]
    return {
        "DIAGNOSE_RULE": DIAGNOSE_RULE,
        "PRIMARY_DIAGNOSIS": PRIMARY_DIAGNOSIS,
        "CANONICAL_ID": CANONICAL_ID,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "NEXT_ACTION": NEXT_ACTION,
        "PIPELINE_EVAL_PASS": bool(eval_receipt.get("PIPELINE_EVAL_PASS")),
        "PIPELINE_EVAL_RECEIPT_SHA256": eval_receipt.get(
            "PIPELINE_EVAL_RECEIPT_SHA256"
        ),
        "findings": findings,
        "root_causes": root_causes,
        "allowed_next_phases": [
            "BUILD_V1R2_STAGE_B_INDEX_UNDER_CANONICAL_STAGE_A",
            "SCOPED_CROSS_SURFACE_COMPARISON_WITHOUT_PROMOTION",
            "HOLD_PACKAGING_LOCAL_ONLY_UNTIL_ALIGNMENT",
        ],
        "forbidden_now": [
            "score_spent_reserve",
            "retrain_stage_a",
            "silent_hub_publish",
            "claim_full_pipeline_pass_on_v1r9",
        ],
        "schema": SCHEMA_DIAGNOSE,
        "train": False,
        "reserve_scored": False,
        "index_rebuilt": False,
    }


def seal_diagnosis_receipt(diagnosis: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(diagnosis)
    payload["PIPELINE_DIAGNOSIS_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in payload.items()
                if k != "PIPELINE_DIAGNOSIS_RECEIPT_SHA256"
            }
        )
    )
    return payload
