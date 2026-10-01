"""HYPERLEX_V5_STAGE_A_CANONICAL_V1 — freeze Stage-A after REPRO promotion.

Binds active Stage-A runtime to the complete factorized checkpoint and
identifiability-filtered contract. No training, no BEST mutation, no
reserve scoring, no Stage-B index rebuild.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .classification_v5_stage_a import (
    BEST_SHA,
    EVIDENCE_LABELS,
    FLAT_RUNTIME_STATUS,
    canonical_json,
    sha256_text,
)
from .classification_v5_stage_a_factorized_objective import (
    OBJECTIVE_ID,
    OBJECTIVE_RECEIPT_SHA256_PIN,
    POSSIBLE_EVIDENCE_STATUS,
    SCHEMA_FORWARD as FACTORIZED_FORWARD_SCHEMA,
    decide_stage_a,
)
from .classification_v5_stage_a_gold_identifiability_contract import (
    CONTRACT_ID,
    MODEL_INPUT,
)
from .classification_v5_stage_a_gold_identifiability_filter import (
    CONTRACT_RECEIPT_SHA256_PIN,
    FILTER_RECEIPT_SHA256_PIN,
    SURFACE_ID,
    V1R2_ANNOTATION_SHA256_PIN,
    V1R2_DATASET_SHA256_PIN,
    V1R2_EXCLUSION_MANIFEST_SHA256_PIN,
)
from .classification_v5_stage_a_ident_filtered_authorize import (
    EXPLICIT_LIMITATIONS,
)
from .classification_v5_stage_a_ident_filtered_promote import (
    CANONICAL_LOAD_SEQUENCE,
    CANONICAL_RELATION_THRESHOLD,
    CANONICAL_RESOLVABILITY_THRESHOLD,
    FLAT_ALLOWED_USES,
)
from .classification_v5_stage_a_ident_filtered_repro_promote import (
    INCOMPLETE_HISTORICAL_CHECKPOINT_SHA256,
    PREVIOUS_STAGE_A_BEST_SHA256,
    STAGE_A_BEST_EPOCH,
    STAGE_A_BEST_SHA256,
)
from .classification_v5_stage_a_two_stage_generalization import (
    SPENT_RESERVE,
    SPENT_RESERVE_STATUS,
)
from .save_pretrained import (
    FACTORIZED_HEAD_NAMES,
    assert_factorized_heads_in_flat,
    require_factorized_heads_in_flat,
)

CANONICAL_ID = "HYPERLEX_V5_STAGE_A_CANONICAL_V1"
FREEZE_RULE = "FREEZE_V5_STAGE_A_CANONICAL_AND_UPDATE_DOWNSTREAM_PROVENANCE"
SCHEMA_CANONICAL = "hyperlex.classification.v5.stage_a_canonical.v1"
SCHEMA_FORWARD = "hyperlex.classification.v5.stage_a_canonical_forward.v1"
COMPAT_FORWARD_SCHEMA = FACTORIZED_FORWARD_SCHEMA

MODEL_WIDE_BEST_SHA256 = BEST_SHA
PARENT_MODEL_WIDE_BEST_SHA256 = BEST_SHA
assert PARENT_MODEL_WIDE_BEST_SHA256 == MODEL_WIDE_BEST_SHA256

PROMOTION_RECEIPT_SHA256 = (
    "9541664c87b27e56d25171579f2ef0b5810a1ebcbbc023298ce2919749f9b370"
)
REPRO_RUN_RECEIPT_SHA256 = (
    "8b8585a8637176a64adf9ce6cff2a076fd4bf938070aef02203fa46978e20ed1"
)
ORIGINAL_SETTLED_RECEIPT_SHA256 = (
    "4a7d565ca607234c604bcec40acab33e3cbecc4da6e4adc86a0b2b79bb091a4b"
)

V5_STAGE_A_STATE = "CANONICAL_FROZEN"
STAGE_A_RESEARCH_LOOP = "CLOSED_FOR_CURRENT_FAILURE_CLASS"

DEPRECATED_RUNTIME = {
    "POSSIBLE_EVIDENCE": POSSIBLE_EVIDENCE_STATUS,
    "Gate1_Gate2_semantics": "HISTORICAL",
    "flat_evidence_head": FLAT_RUNTIME_STATUS,
    "decide_evidence_P_PRESENT": "HISTORICAL_COMPATIBILITY_ONLY",
    "two_stage_forward_schema": "HISTORICAL",
}

KNOWN_LIMITATIONS = {
    "DOMAIN_IRRELEVANT_GENERALIZATION": "NOT_ESTABLISHED",
    "SHORT_ATOM_POSITIVE_GENERALIZATION": "LOW_SUPPORT",
    "CONTEXT_DEPENDENT_GOLD": "OUTSIDE_CURRENT_TEXT_ONLY_STAGE_A_CONTRACT",
}

CENTRAL_SCIENTIFIC_CONCLUSION = (
    "Gold/input identifiability repair, not architecture escalation, "
    "resolved the dominant Stage-A failure."
)

AUTO_RELABEL = False
REQUIRED_FACTORIZED_KEYS = (
    "relation_head.weight",
    "relation_head.bias",
    "resolvability_head.weight",
    "resolvability_head.bias",
)


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def decide_canonical_stage_a(
    *,
    p_relation: float,
    p_resolvable: float,
) -> str:
    return decide_stage_a(
        p_evidence_relation_present=float(p_relation),
        p_resolvable=float(p_resolvable),
        relation_threshold=CANONICAL_RELATION_THRESHOLD,
        resolvability_threshold=CANONICAL_RESOLVABILITY_THRESHOLD,
    )


def stage_b_entry_from_stage_a(evidence_decision: str) -> dict[str, Any]:
    label = str(evidence_decision)
    if label not in EVIDENCE_LABELS:
        raise ValueError(f"unknown_stage_a_decision:{label}")
    if label == "EVIDENCE_PRESENT":
        return {
            "action": "PERMIT_STAGE_B",
            "evidence_decision": label,
            "family_retrieval": "PERMITTED",
            "stage_b_permitted": True,
        }
    if label == "NO_EVIDENCE":
        return {
            "action": "STOP",
            "evidence_decision": label,
            "family_retrieval": "FORBIDDEN",
            "stage_b_permitted": False,
        }
    return {
        "action": "ABSTAIN",
        "evidence_decision": label,
        "family_retrieval": "FORBIDDEN",
        "stage_b_permitted": False,
        "note": "UNCERTAIN stops before family retrieval",
    }


def may_invoke_stage_b(evidence_decision: str) -> bool:
    return bool(stage_b_entry_from_stage_a(evidence_decision)["stage_b_permitted"])


def verify_canonical_checkpoint_keys(tensor_keys: Sequence[str]) -> dict[str, Any]:
    keys = set(str(k) for k in tensor_keys)
    present = {k: k in keys for k in REQUIRED_FACTORIZED_KEYS}
    has_encoder = any(k.startswith("encoder.") for k in keys)
    legacy = {
        "evidence_head": any(k.startswith("evidence_head.") for k in keys),
        "gate1_head": any(k.startswith("gate1_head.") for k in keys),
        "gate2_head": any(k.startswith("gate2_head.") for k in keys),
    }
    flat_check = require_factorized_heads_in_flat({k: None for k in keys})
    # Shape check skipped when values are None; presence-only path:
    presence_ok = all(present.values()) and has_encoder and not any(legacy.values())
    return {
        "pass": presence_ok and not flat_check["missing"],
        "n_keys": len(keys),
        "required_keys_present": present,
        "has_adapted_encoder": has_encoder,
        "legacy_heads_present": legacy,
        "factorized_head_names": list(FACTORIZED_HEAD_NAMES),
        "incomplete_historical_refused": INCOMPLETE_HISTORICAL_CHECKPOINT_SHA256,
    }


def assert_canonical_factorized_flat(tensors: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed on incomplete factorized serialization (regression guard)."""
    return assert_factorized_heads_in_flat(tensors)


def gold_identifiability_binding() -> dict[str, Any]:
    return {
        "AUTO_RELABEL": AUTO_RELABEL,
        "CONTRACT_ID": CONTRACT_ID,
        "CONTRACT_RECEIPT_SHA256": CONTRACT_RECEIPT_SHA256_PIN,
        "FILTER_RECEIPT_SHA256": FILTER_RECEIPT_SHA256_PIN,
        "MODEL_INPUT": list(MODEL_INPUT),
        "SURFACE_ID": SURFACE_ID,
        "V1R2_ANNOTATION_SHA256": V1R2_ANNOTATION_SHA256_PIN,
        "V1R2_DATASET_SHA256": V1R2_DATASET_SHA256_PIN,
        "V1R2_EXCLUSION_MANIFEST_SHA256": V1R2_EXCLUSION_MANIFEST_SHA256_PIN,
        "canonical_rule": (
            "If MODEL_INPUT=text, definitive supervised gold must be "
            "identifiable from text."
        ),
        "context_dependent_definitive_gold": "EXCLUDED_FROM_ACTIVE_SUPERVISION",
        "historical_v1r1_and_excluded_rows": "RETAINED_AS_EVIDENCE",
    }


def canonical_inference_policy() -> str:
    return (
        "if P(RESOLVABLE) < 0.75 -> UNCERTAIN; "
        "else if P(EVIDENCE_RELATION_PRESENT) >= 0.60 -> EVIDENCE_PRESENT; "
        "else NO_EVIDENCE"
    )


def build_canonical_forward(
    *,
    stage_a_decision: str,
    p_relation: float,
    p_resolvable: float,
    stage_a_checkpoint_sha: str | None = None,
    parent_model_wide_best_sha: str | None = None,
) -> dict[str, Any]:
    """Single Stage-A forward contract for active downstream consumers."""
    decision = str(stage_a_decision)
    if decision not in EVIDENCE_LABELS:
        raise ValueError(f"unknown_stage_a_decision:{decision}")
    payload = {
        "schema": SCHEMA_FORWARD,
        "compatibility_schema": COMPAT_FORWARD_SCHEMA,
        "compatibility_adapter": "DEPRECATED_USE_CANONICAL_FORWARD",
        "stage_a_decision": decision,
        "p_relation": float(p_relation),
        "p_resolvable": float(p_resolvable),
        "relation_threshold": CANONICAL_RELATION_THRESHOLD,
        "resolvability_threshold": CANONICAL_RESOLVABILITY_THRESHOLD,
        "stage_a_checkpoint_sha": stage_a_checkpoint_sha or STAGE_A_BEST_SHA256,
        "parent_model_wide_best_sha": (
            parent_model_wide_best_sha or PARENT_MODEL_WIDE_BEST_SHA256
        ),
        "objective_version": OBJECTIVE_ID,
        "input_contract_version": CONTRACT_ID,
        "canonical_id": CANONICAL_ID,
        "semantic_outputs": list(EVIDENCE_LABELS),
        "internal_fields": ["p_relation", "p_resolvable"],
    }
    # Legacy alias fields for transitional callers (deprecated).
    payload["legacy_aliases"] = {
        "evidence_decision": decision,
        "P_PRESENT": float(p_relation),
        "status": "DEPRECATED_COMPATIBILITY_ONLY",
    }
    return payload


def deprecated_runtime_status() -> dict[str, Any]:
    return {
        **DEPRECATED_RUNTIME,
        "allowed_historical_uses": list(FLAT_ALLOWED_USES),
        "previous_STAGE_A_BEST": {
            "checkpoint_sha256": PREVIOUS_STAGE_A_BEST_SHA256,
            "status": "SUPERSEDED_STAGE_A_BEST",
        },
        "incomplete_packaging_artifact": {
            "checkpoint_sha256": INCOMPLETE_HISTORICAL_CHECKPOINT_SHA256,
            "status": "NON_PROMOTABLE_PACKAGING_ARTIFACT",
        },
        "historical_artifacts_deleted": False,
    }


def stage_a_canonical_contract() -> dict[str, Any]:
    return {
        "CANONICAL_ID": CANONICAL_ID,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "STAGE_A_BEST_EPOCH": STAGE_A_BEST_EPOCH,
        "V5_STAGE_A_STATE": V5_STAGE_A_STATE,
        "STAGE_A_RESEARCH_LOOP": STAGE_A_RESEARCH_LOOP,
        "auto_relabel": AUTO_RELABEL,
        "central_scientific_conclusion": CENTRAL_SCIENTIFIC_CONCLUSION,
        "decision_outputs": list(EVIDENCE_LABELS),
        "deprecated_runtime": deprecated_runtime_status(),
        "forward_schema": SCHEMA_FORWARD,
        "gold_identifiability": gold_identifiability_binding(),
        "inference_policy": canonical_inference_policy(),
        "internal_semantics": ["p_relation", "p_resolvable"],
        "known_limitations": dict(KNOWN_LIMITATIONS),
        "load_sequence": list(CANONICAL_LOAD_SEQUENCE),
        "model_input": list(MODEL_INPUT),
        "objective_id": OBJECTIVE_ID,
        "objective_receipt_sha256": OBJECTIVE_RECEIPT_SHA256_PIN,
        "parent_model_wide_best": PARENT_MODEL_WIDE_BEST_SHA256,
        "promotion_receipt_sha256": PROMOTION_RECEIPT_SHA256,
        "relation_threshold": CANONICAL_RELATION_THRESHOLD,
        "repro_run_receipt_sha256": REPRO_RUN_RECEIPT_SHA256,
        "original_settled_receipt_sha256": ORIGINAL_SETTLED_RECEIPT_SHA256,
        "required_factorized_keys": list(REQUIRED_FACTORIZED_KEYS),
        "resolvability_threshold": CANONICAL_RESOLVABILITY_THRESHOLD,
        "reserve": SPENT_RESERVE,
        "reserve_status": SPENT_RESERVE_STATUS,
        "schema": SCHEMA_CANONICAL,
        "serialization": {
            "factorized_heads_required": True,
            "factorized_head_names": list(FACTORIZED_HEAD_NAMES),
            "fail_closed_if_incomplete": True,
            "head_drop_regression_covered": True,
        },
        "surface_id": SURFACE_ID,
        "explicit_limitations": dict(EXPLICIT_LIMITATIONS),
    }


def build_canonical_freeze_receipt(
    *,
    code_revision: str,
    stale_reference_audit: Mapping[str, Any] | None = None,
    frozen_at: str | None = None,
) -> dict[str, Any]:
    payload = {
        "BEST_MUTATED": False,
        "CANONICAL_ID": CANONICAL_ID,
        "FREEZE_RULE": FREEZE_RULE,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "NEXT_ACTION": "EVALUATE_FULL_V5_PIPELINE_OR_PRODUCTION_PACKAGING",
        "RESERVE_CONSUMED": False,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "STAGE_A_RESEARCH_LOOP": STAGE_A_RESEARCH_LOOP,
        "TRAIN": False,
        "V5_STAGE_A_STATE": V5_STAGE_A_STATE,
        "code_revision": code_revision,
        "contract": stage_a_canonical_contract(),
        "frozen_at": frozen_at or utc_now_iso(),
        "schema": SCHEMA_CANONICAL,
        "stale_reference_audit": dict(stale_reference_audit or {}),
    }
    payload["STAGE_A_CANONICAL_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in payload.items()
                if k != "STAGE_A_CANONICAL_RECEIPT_SHA256"
            }
        )
    )
    return payload
