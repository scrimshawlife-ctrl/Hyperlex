"""V5 production packaging contract — local load shape, not Hub publish.

Binds frozen Stage-A/B artifacts into a single packaging manifest.
Does not upload to Hub, train, rebuild index, or score reserve.
"""

from __future__ import annotations

from typing import Any, Mapping

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_b_pipeline import PIPELINE_ID, PIPELINE_FLOW
from .classification_v5_stage_a_canonical import (
    CANONICAL_ID,
    KNOWN_LIMITATIONS,
    MODEL_WIDE_BEST_SHA256,
    SCHEMA_FORWARD,
    STAGE_A_BEST_SHA256,
    V5_STAGE_A_STATE,
    canonical_inference_policy,
)
from .classification_v5_stage_a_gold_identifiability_contract import (
    CONTRACT_ID,
    MODEL_INPUT,
)
from .classification_v5_stage_a_ident_filtered_promote import (
    CANONICAL_LOAD_SEQUENCE,
    CANONICAL_RELATION_THRESHOLD,
    CANONICAL_RESOLVABILITY_THRESHOLD,
)
from .classification_v5_stage_b import (
    FROZEN_INDEX_SHA256,
    FROZEN_MINIMUM_FAMILY_SCORE,
    FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
    STAGE_B_RULE,
)
from .save_pretrained import FACTORIZED_HEAD_NAMES

PACKAGING_ID = "HYPERLEX_V5_PRODUCTION_PACKAGING_V1"
PACKAGING_RULE = "SEAL_V5_PRODUCTION_PACKAGING_CONTRACT"
SCHEMA_PACKAGING = "hyperlex.classification.v5.production_packaging.v1"
HUB_STATUS = "NOT_AUTHORIZED"
NEXT_ACTION = "OPERATOR_HUB_PUBLISH_GATE_OR_LOCAL_DEPLOY_RUNBOOK"

LOCAL_WEIGHT_LAYOUT = {
    "trunk": "~/.hyperlex/models/trunks/ModernBERT-base",
    "model_wide_best": (
        "~/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
        "model.safetensors"
    ),
    "stage_a_best": "~/.hyperlex/models/STAGE_A_BEST/model.safetensors",
    "stage_b_index": (
        "~/.hyperlex/hlx-private-or-operator-path/"
        "classification-v5-stage-b-*/STAGE_B_INDEX.json"
    ),
}


def packaging_contract(
    *,
    pipeline_eval_receipt_sha256: str | None = None,
    pipeline_eval_pass: bool | None = None,
) -> dict[str, Any]:
    return {
        "PACKAGING_ID": PACKAGING_ID,
        "HUB_STATUS": HUB_STATUS,
        "PIPELINE_ID": PIPELINE_ID,
        "STAGE_A_CANONICAL": CANONICAL_ID,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "STAGE_B_RULE": STAGE_B_RULE,
        "STAGE_B_INDEX_SHA256": FROZEN_INDEX_SHA256,
        "V5_STAGE_A_STATE": V5_STAGE_A_STATE,
        "artifacts": {
            "stage_a_checkpoint_sha256": STAGE_A_BEST_SHA256,
            "model_wide_best_sha256": MODEL_WIDE_BEST_SHA256,
            "stage_b_index_sha256": FROZEN_INDEX_SHA256,
            "stage_b_minimum_family_score": FROZEN_MINIMUM_FAMILY_SCORE,
            "stage_b_minimum_top1_top2_margin": FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
            "relation_threshold": CANONICAL_RELATION_THRESHOLD,
            "resolvability_threshold": CANONICAL_RESOLVABILITY_THRESHOLD,
            "forward_schema": SCHEMA_FORWARD,
            "gold_contract_id": CONTRACT_ID,
            "pipeline_eval_receipt_sha256": pipeline_eval_receipt_sha256,
            "pipeline_eval_pass": pipeline_eval_pass,
        },
        "factorized_heads": list(FACTORIZED_HEAD_NAMES),
        "flow": list(PIPELINE_FLOW),
        "inference_policy": canonical_inference_policy(),
        "known_limitations": dict(KNOWN_LIMITATIONS),
        "load_sequence": list(CANONICAL_LOAD_SEQUENCE),
        "local_weight_layout": dict(LOCAL_WEIGHT_LAYOUT),
        "model_input": list(MODEL_INPUT),
        "publish_authorized": False,
        "schema": SCHEMA_PACKAGING,
        "weights_in_git": False,
    }


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
    )
    payload = {
        "BEST_MUTATED": False,
        "HUB_STATUS": HUB_STATUS,
        "NEXT_ACTION": NEXT_ACTION if pipeline_eval_pass else "DIAGNOSE_V5_PIPELINE_BEFORE_PACKAGING",
        "PACKAGING_ID": PACKAGING_ID,
        "PACKAGING_RULE": PACKAGING_RULE,
        "PIPELINE_EVAL_PASS": pipeline_eval_pass,
        "PIPELINE_EVAL_RECEIPT_SHA256": pipeline_eval_receipt_sha256,
        "RESERVE_CONSUMED": False,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "TRAIN": False,
        "code_revision": code_revision,
        "contract": contract,
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
    return f"""## V5 classification pipeline (local; Hub unpublished)

**Packaging ID:** `{PACKAGING_ID}`
**Pipeline:** `{PIPELINE_ID}` · Stage-A `{CANONICAL_ID}`

| Artifact | SHA256 / value |
| --- | --- |
| `STAGE_A_BEST` | `{STAGE_A_BEST_SHA256}` |
| `MODEL_WIDE_BEST` | `{MODEL_WIDE_BEST_SHA256}` |
| Stage-B index | `{FROZEN_INDEX_SHA256}` |
| Stage-B floors | score `{FROZEN_MINIMUM_FAMILY_SCORE}`, margin `{FROZEN_MINIMUM_TOP1_TOP2_MARGIN}` |
| Stage-A thresholds | relation `{CANONICAL_RELATION_THRESHOLD}`, resolvability `{CANONICAL_RESOLVABILITY_THRESHOLD}` |

**Load sequence:** ModernBERT trunk → MODEL_WIDE_BEST → STAGE_A_BEST (layers 20/21 + `relation_head` + `resolvability_head`).

**Decision:** `{canonical_inference_policy()}`

**Stage B:** only on `EVIDENCE_PRESENT`. Index not rebuilt under this packaging.

**Limitations:** DOMAIN_IRRELEVANT=`NOT_ESTABLISHED`; SHORT_ATOM_POSITIVE=`LOW_SUPPORT`; CONTEXT_DEPENDENT_GOLD=`OUTSIDE_CURRENT_TEXT_ONLY_STAGE_A_CONTRACT`.

**Hub:** `{HUB_STATUS}`. Weights stay on operator Spark paths; not in git.
"""
