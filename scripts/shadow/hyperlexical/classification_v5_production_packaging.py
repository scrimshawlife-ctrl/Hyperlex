"""V5 production packaging — local V1R2 Stage-A/B package, not Hub publish.

Delegates to SEAL_AND_PACKAGE_HYPERLEX_V5_STAGE_A_B_V1R2_PIPELINE for the
active package contract. Does not upload to Hub, train, rebuild index, or
score reserve.
"""

from __future__ import annotations

from typing import Any

from .classification_v5_seal_and_package import (
    HUB_STATUS,
    LOCAL_WEIGHT_LAYOUT,
    NEXT_ACTION_CLEAN,
    PACKAGING_ID,
    SEAL_RULE,
    hf_card_section as _hf_card_section,
    package_contract as _package_contract,
)
from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_b_pipeline import PIPELINE_ID
from .classification_v5_stage_a_canonical import (
    CANONICAL_ID,
    MODEL_WIDE_BEST_SHA256,
    STAGE_A_BEST_SHA256,
    canonical_inference_policy,
)
from .classification_v5_stage_a_ident_filtered_promote import (
    CANONICAL_RELATION_THRESHOLD,
    CANONICAL_RESOLVABILITY_THRESHOLD,
)
from .classification_v5_stage_b import (
    FROZEN_INDEX_SHA256,
    FROZEN_MINIMUM_FAMILY_SCORE,
    FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
)

PACKAGING_RULE = SEAL_RULE
SCHEMA_PACKAGING = "hyperlex.classification.v5.production_packaging.v1"
NEXT_ACTION = NEXT_ACTION_CLEAN


def packaging_contract(
    *,
    pipeline_eval_receipt_sha256: str | None = None,
    pipeline_eval_pass: bool | None = None,
    code_revision: str = "local",
) -> dict[str, Any]:
    contract = _package_contract(code_revision=code_revision)
    contract["schema"] = SCHEMA_PACKAGING
    contract["PACKAGING_RULE"] = PACKAGING_RULE
    contract["artifacts"]["pipeline_eval_receipt_sha256"] = pipeline_eval_receipt_sha256
    contract["artifacts"]["pipeline_eval_pass"] = pipeline_eval_pass
    # Compatibility alias for older packaging tests/callers.
    contract["artifacts_legacy"] = {
        "stage_a_checkpoint_sha256": STAGE_A_BEST_SHA256,
        "model_wide_best_sha256": MODEL_WIDE_BEST_SHA256,
        "stage_b_index_sha256": FROZEN_INDEX_SHA256,
        "stage_b_minimum_family_score": FROZEN_MINIMUM_FAMILY_SCORE,
        "stage_b_minimum_top1_top2_margin": FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
        "pipeline_eval_receipt_sha256": pipeline_eval_receipt_sha256,
        "pipeline_eval_pass": pipeline_eval_pass,
    }
    return contract


def build_packaging_receipt(
    *,
    code_revision: str,
    pipeline_eval_receipt_sha256: str,
    pipeline_eval_pass: bool,
    sealed_at: str,
) -> dict[str, Any]:
    contract = packaging_contract(
        pipeline_eval_receipt_sha256=pipeline_eval_receipt_sha256,
        pipeline_eval_pass=pipeline_eval_pass,
        code_revision=code_revision,
    )
    payload = {
        "BEST_MUTATED": False,
        "HUB_STATUS": HUB_STATUS,
        "NEXT_ACTION": NEXT_ACTION if pipeline_eval_pass else "DIAGNOSE_V5_PIPELINE_BEFORE_PACKAGING",
        "PACKAGING_ID": PACKAGING_ID,
        "PACKAGING_RULE": PACKAGING_RULE,
        "PIPELINE_EVAL_PASS": pipeline_eval_pass,
        "PIPELINE_EVAL_RECEIPT_SHA256": pipeline_eval_receipt_sha256,
        "PIPELINE_DEPENDENCY_MANIFEST_SHA256": contract[
            "PIPELINE_DEPENDENCY_MANIFEST_SHA256"
        ],
        "RESERVE_CONSUMED": False,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "TRAIN": False,
        "code_revision": code_revision,
        "contract": contract,
        "local_weight_layout": dict(LOCAL_WEIGHT_LAYOUT),
        "schema": SCHEMA_PACKAGING,
        "sealed_at": sealed_at,
    }
    payload["PACKAGING_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {k: v for k, v in payload.items() if k != "PACKAGING_RECEIPT_SHA256"}
        )
    )
    return payload


def hf_package_v5_card_section() -> str:
    """Markdown fragment for Spec 007 hf-package / model-card surfaces."""
    return _hf_card_section()
