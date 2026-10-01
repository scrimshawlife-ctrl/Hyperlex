"""PROMOTE_V5_STAGE_A_TWO_STAGE_SELECTED — component-scoped Stage-A promotion.

Promotes SELECTED two-stage checkpoint to STAGE_A_BEST. Does not retrain,
alter thresholds/V1R9/weights, score reserve, or mutate model-wide BEST.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .classification_v5_stage_a import (
    BEST_SHA,
    EVIDENCE_LABELS,
    FLAT_RUNTIME_STATUS as STAGE_A_FLAT_RUNTIME_STATUS,
    canonical_json,
    sha256_text,
)
from .classification_v5_stage_a_two_stage import (
    ARCHITECTURE_RECEIPT_SHA256,
    AUTHORIZED_AUTH_RECEIPT_SHA256,
    AUTHORIZED_BEST_SHA,
    AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
    AUTHORIZED_DATASET_SHA,
    AUTHORIZED_TRAINING_CONFIG_SHA256,
    CANONICAL_FORWARD_SCHEMA as TWO_STAGE_CANONICAL_FORWARD,
    EXPERIMENT_ID,
    FLAT_HEAD_STATUS,
    TWO_STAGE_RULE,
    decide_two_stage,
)
from .classification_v5_stage_a_two_stage_promotion_review import (
    EXPECTED_GATE1_THRESHOLD,
    EXPECTED_GATE2_PRESENT_THRESHOLD,
    EXPECTED_METRICS,
    EXPECTED_RUN_RECEIPT_SHA256,
    EXPECTED_SELECTED_CHECKPOINT_SHA256,
    EXPECTED_SELECTED_EPOCH,
    EXPECTED_SPLIT_WITNESS_SHA256,
    KNOWN_LIMITATIONS,
    PROMOTE_ACTION,
    metric_parity,
    replay_decisions,
    verify_architecture_identity,
)

PROMOTE_RULE = "PROMOTE_V5_STAGE_A_TWO_STAGE_SELECTED"
SCHEMA_PROMOTION = "hyperlex.classification.v5.stage_a_two_stage_promotion.v1"
SCHEMA_STAGE_A_BEST = "hyperlex.classification.v5.stage_a_best_pointer.v1"

# Flat path retained for historical replay / scientific comparison only.
FLAT_RUNTIME_STATUS = STAGE_A_FLAT_RUNTIME_STATUS
FLAT_ALLOWED_USES = (
    "historical_replay",
    "scientific_comparison",
    "compatibility_diagnostics",
)

STAGE_A_BEST_SHA256 = EXPECTED_SELECTED_CHECKPOINT_SHA256
STAGE_A_BEST_EPOCH = EXPECTED_SELECTED_EPOCH
CANONICAL_GATE1_THRESHOLD = EXPECTED_GATE1_THRESHOLD
CANONICAL_GATE2_THRESHOLD = EXPECTED_GATE2_PRESENT_THRESHOLD
PARENT_ENCODER_BEST_SHA256 = AUTHORIZED_BEST_SHA
MODEL_WIDE_BEST_SHA256 = BEST_SHA
assert PARENT_ENCODER_BEST_SHA256 == MODEL_WIDE_BEST_SHA256 == AUTHORIZED_BEST_SHA

PROMOTION_REVIEW_RECEIPT_SHA256 = (
    "7e09c67d474c91af58dd4f2b4f19121ee81e99d5d472282cf0b4880a638908f2"
)
VALIDATION_REPLAY_HASH = (
    "fc601e69569594d55eb150ee9b467eb37ce0c1b3015e29d88d54aecb7eda6474"
)

CANONICAL_LOAD_SEQUENCE = (
    "modernbert_trunk",
    "model_wide_BEST_encoder_overlay",
    "STAGE_A_BEST_adapted_layers_20_21",
    "gate1_head",
    "gate2_head",
)

CANONICAL_INFERENCE_POLICY = (
    "if P(POSSIBLE_EVIDENCE) < 0.75 -> NO_EVIDENCE; "
    "else if P(CONFIRMED_PRESENT) >= 0.50 -> EVIDENCE_PRESENT; "
    "else UNCERTAIN"
)

CANONICAL_FORWARD_SCHEMA = TWO_STAGE_CANONICAL_FORWARD

# Rounded display targets from the operator CLEAR (exact floats in EXPECTED_METRICS).
DISPLAY_METRICS = {
    "false_entry": 0.0423,
    "PRESENT_recall": 0.7049,
    "NONE_recall": 0.9089,
    "UNCERTAIN_recall": 0.6790,
    "e2e_macro_F1": 0.7411,
}


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def preflight_promotion(
    *,
    promotion_review: Mapping[str, Any],
    validation_replay: Mapping[str, Any],
    train_receipt: Mapping[str, Any],
    selected_checkpoint_sha256: str,
    model_wide_best_sha256: str,
) -> dict[str, Any]:
    checks = {
        "promotion_review_valid": promotion_review.get("PROMOTION_REVIEW") == "VALID",
        "promotion_decision_ready": promotion_review.get("PROMOTION_DECISION")
        == "PROMOTION_READY",
        "promotion_review_receipt": promotion_review.get("review_receipt_sha256")
        == PROMOTION_REVIEW_RECEIPT_SHA256,
        "validation_replay_hash": validation_replay.get("replay_hash")
        == VALIDATION_REPLAY_HASH
        and bool(validation_replay.get("pass")),
        "selected_checkpoint": selected_checkpoint_sha256
        == STAGE_A_BEST_SHA256
        and promotion_review.get("SELECTED_CHECKPOINT_SHA256")
        == STAGE_A_BEST_SHA256
        and train_receipt.get("SELECTED_CHECKPOINT_SHA256") == STAGE_A_BEST_SHA256,
        "selected_epoch": int(promotion_review.get("SELECTED_EPOCH") or -1)
        == STAGE_A_BEST_EPOCH
        and int(train_receipt.get("restored_epoch") or -1) == STAGE_A_BEST_EPOCH,
        "scientific_settled_pass": train_receipt.get("SCIENTIFIC_RESULT")
        == "SETTLED_PASS",
        "model_wide_best_unchanged_pin": model_wide_best_sha256
        == MODEL_WIDE_BEST_SHA256,
        "promote_action_name": promotion_review.get("NEXT_ACTION") == PROMOTE_ACTION
        or promotion_review.get("NEXT_ACTION") == PROMOTE_RULE,
        "thresholds_frozen": float(
            (train_receipt.get("selected_thresholds") or {}).get("gate1_threshold")
        )
        == CANONICAL_GATE1_THRESHOLD
        and float(
            (train_receipt.get("selected_thresholds") or {}).get(
                "gate2_present_threshold"
            )
        )
        == CANONICAL_GATE2_THRESHOLD,
    }
    return {
        "checks": checks,
        "pass": all(checks.values()),
        "result": "PASS" if all(checks.values()) else "FAIL_CLOSED",
    }


def canonical_load_contract() -> dict[str, Any]:
    return {
        "architecture": TWO_STAGE_RULE,
        "fail_closed_if": [
            "parent_BEST_sha_mismatch",
            "stage_a_overlay_name_or_shape_mismatch",
            "missing_gate1_or_gate2_head",
            "flat_evidence_head_loaded_as_canonical",
        ],
        "forward_schema": CANONICAL_FORWARD_SCHEMA,
        "gate1_threshold": CANONICAL_GATE1_THRESHOLD,
        "gate2_threshold": CANONICAL_GATE2_THRESHOLD,
        "parent_encoder_best": PARENT_ENCODER_BEST_SHA256,
        "runtime_threshold_search": False,
        "sequence": list(CANONICAL_LOAD_SEQUENCE),
        "stage_a_best": STAGE_A_BEST_SHA256,
    }


def decide_canonical_stage_a(
    *,
    p_possible: float,
    p_confirmed: float,
) -> str:
    """Promoted runtime decision — frozen thresholds, no search."""
    return decide_two_stage(
        p_possible=float(p_possible),
        p_confirmed=float(p_confirmed),
        gate1_threshold=CANONICAL_GATE1_THRESHOLD,
        gate2_present_threshold=CANONICAL_GATE2_THRESHOLD,
    )


def stage_b_entry_from_stage_a(evidence_decision: str) -> dict[str, Any]:
    """Downstream adapter: Stage-B sees semantic labels only, not Gate1/Gate2."""
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
    # UNCERTAIN
    return {
        "action": "ABSTAIN",
        "evidence_decision": label,
        "family_retrieval": "FORBIDDEN",
        "stage_b_permitted": False,
        "note": "UNCERTAIN stops before family retrieval",
    }


def may_invoke_stage_b(evidence_decision: str) -> bool:
    return bool(stage_b_entry_from_stage_a(evidence_decision)["stage_b_permitted"])


def flat_runtime_deprecation() -> dict[str, Any]:
    return {
        "allowed_uses": list(FLAT_ALLOWED_USES),
        "canonical_runtime": False,
        "design_status": FLAT_HEAD_STATUS,
        "fallback_to_scalar_p_present": False,
        "status": FLAT_RUNTIME_STATUS,
    }


def build_stage_a_best_pointer(
    *,
    weights_path: str,
    previous_stage_a_best: str | None,
    code_revision: str,
    promoted_at: str | None = None,
) -> dict[str, Any]:
    return {
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "STAGE_A_BEST_EPOCH": STAGE_A_BEST_EPOCH,
        "architecture": TWO_STAGE_RULE,
        "architecture_receipt_sha256": ARCHITECTURE_RECEIPT_SHA256,
        "checkpoint_sha256": STAGE_A_BEST_SHA256,
        "code_revision": code_revision,
        "component": "STAGE_A",
        "experiment_id": EXPERIMENT_ID,
        "forward_schema": CANONICAL_FORWARD_SCHEMA,
        "gate1_threshold": CANONICAL_GATE1_THRESHOLD,
        "gate2_threshold": CANONICAL_GATE2_THRESHOLD,
        "load_sequence": list(CANONICAL_LOAD_SEQUENCE),
        "model_wide_BEST": MODEL_WIDE_BEST_SHA256,
        "model_wide_BEST_mutated": False,
        "parent_encoder_best": PARENT_ENCODER_BEST_SHA256,
        "previous_STAGE_A_BEST": previous_stage_a_best,
        "promoted_at": promoted_at or utc_now_iso(),
        "promotion_rule": PROMOTE_RULE,
        "schema": SCHEMA_STAGE_A_BEST,
        "semantic_outputs": list(EVIDENCE_LABELS),
        "weights_path": weights_path,
    }


def verify_canonical_overlay(
    *,
    parent_best_sha256: str,
    stage_a_tensor_keys: Sequence[str],
) -> dict[str, Any]:
    arch = verify_architecture_identity(stage_a_tensor_keys)
    checks = {
        "parent_best_matches": parent_best_sha256 == PARENT_ENCODER_BEST_SHA256,
        "architecture_identity": bool(arch.get("pass")),
        "no_flat_evidence_head_canonical": bool(
            (arch.get("checks") or {}).get("no_flat_evidence_head")
        ),
        "has_gate1_and_gate2": bool((arch.get("checks") or {}).get("has_gate1_head"))
        and bool((arch.get("checks") or {}).get("has_gate2_head")),
    }
    return {
        "architecture": arch,
        "checks": checks,
        "pass": all(checks.values()),
    }


def post_promotion_replay_check(
    *,
    golds: Sequence[str],
    p_possible: Sequence[float],
    p_confirmed: Sequence[float],
) -> dict[str, Any]:
    replay = replay_decisions(
        golds=golds,
        p_possible=p_possible,
        p_confirmed=p_confirmed,
        gate1_threshold=CANONICAL_GATE1_THRESHOLD,
        gate2_present_threshold=CANONICAL_GATE2_THRESHOLD,
    )
    # Exact parity with sealed promotion-review EXPECTED_METRICS.
    exact = metric_parity(
        {k: replay["metrics"][k] for k in EXPECTED_METRICS},
        EXPECTED_METRICS,
    )
    hash_ok = replay["replay_hash"] == VALIDATION_REPLAY_HASH
    return {
        "display_targets": dict(DISPLAY_METRICS),
        "exact_parity": exact,
        "metrics": replay["metrics"],
        "pass": bool(exact["pass"] and hash_ok and replay["thresholds_match"]),
        "replay_hash": replay["replay_hash"],
        "replay_hash_matches_review": hash_ok,
        "thresholds_match": replay["thresholds_match"],
    }


def choose_promotion_state(
    *,
    preflight_pass: bool,
    overlay_pass: bool,
    post_replay_pass: bool,
) -> dict[str, Any]:
    if not preflight_pass:
        return {
            "STAGE_A_PROMOTION": "BLOCKED",
            "PROMOTION_INVALID": False,
            "applied": False,
            "reason": "preflight_failed",
        }
    if not overlay_pass:
        return {
            "STAGE_A_PROMOTION": "BLOCKED",
            "PROMOTION_INVALID": False,
            "applied": False,
            "reason": "overlay_verification_failed",
        }
    if not post_replay_pass:
        return {
            "STAGE_A_PROMOTION": "PROMOTION_INVALID",
            "PROMOTION_INVALID": True,
            "applied": False,
            "reason": "post_promotion_replay_mismatch",
            "restore_previous_STAGE_A_BEST": True,
        }
    return {
        "STAGE_A_PROMOTION": "APPLIED",
        "PROMOTION_INVALID": False,
        "applied": True,
        "reason": "ok",
    }


def build_promotion_receipt(
    *,
    preflight: Mapping[str, Any],
    pointer: Mapping[str, Any],
    overlay: Mapping[str, Any],
    post_replay: Mapping[str, Any],
    previous_stage_a_best: str | None,
    code_revision: str,
    promoted_at: str | None = None,
) -> dict[str, Any]:
    state = choose_promotion_state(
        preflight_pass=bool(preflight.get("pass")),
        overlay_pass=bool(overlay.get("pass")),
        post_replay_pass=bool(post_replay.get("pass")),
    )
    payload = {
        "ARCHITECTURE_RECEIPT_SHA256": ARCHITECTURE_RECEIPT_SHA256,
        "AUTHORIZATION_RECEIPT_SHA256": AUTHORIZED_AUTH_RECEIPT_SHA256,
        "BEST_MUTATED": False,
        "CLASS_WEIGHT_ARTIFACT_SHA256": AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
        "DATASET_SHA256": AUTHORIZED_DATASET_SHA,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "NEXT_ACTION": (
            "STOP_STAGE_A_ARCHITECTURE_WORK"
            if state["applied"]
            else "STOP"
        ),
        "PARENT_ENCODER_BEST": PARENT_ENCODER_BEST_SHA256,
        "PROMOTION_INVALID": state["PROMOTION_INVALID"],
        "PROMOTION_REVIEW_RECEIPT_SHA256": PROMOTION_REVIEW_RECEIPT_SHA256,
        "PROMOTE_RULE": PROMOTE_RULE,
        "RESERVE_CONSUMED": False,
        "RUN_RECEIPT_SHA256": EXPECTED_RUN_RECEIPT_SHA256,
        "SELECTED_CHECKPOINT_SHA256": STAGE_A_BEST_SHA256,
        "SELECTED_EPOCH": STAGE_A_BEST_EPOCH,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256 if state["applied"] else previous_stage_a_best,
        "STAGE_A_PROMOTION": state["STAGE_A_PROMOTION"],
        "TRAIN": False,
        "TRAINING_CONFIG_SHA256": AUTHORIZED_TRAINING_CONFIG_SHA256,
        "TWO_STAGE_SPLIT_WITNESS_SHA256": EXPECTED_SPLIT_WITNESS_SHA256,
        "VALIDATION_REPLAY_HASH": VALIDATION_REPLAY_HASH,
        "architecture": TWO_STAGE_RULE,
        "canonical_forward_schema": CANONICAL_FORWARD_SCHEMA,
        "canonical_inference_policy": CANONICAL_INFERENCE_POLICY,
        "canonical_load_path": canonical_load_contract(),
        "canonical_thresholds": {
            "gate1_threshold": CANONICAL_GATE1_THRESHOLD,
            "gate2_threshold": CANONICAL_GATE2_THRESHOLD,
        },
        "code_revision": code_revision,
        "flat_runtime": flat_runtime_deprecation(),
        "known_limitations": list(KNOWN_LIMITATIONS),
        "overlay_verification": dict(overlay),
        "pointer": dict(pointer) if state["applied"] else None,
        "post_promotion_replay": dict(post_replay),
        "preflight": dict(preflight),
        "previous_STAGE_A_BEST": previous_stage_a_best,
        "promoted_at": promoted_at or utc_now_iso(),
        "runtime_adapter": {
            "decide_canonical_stage_a": "decide_two_stage(p_possible,p_confirmed)",
            "semantic_outputs": list(EVIDENCE_LABELS),
            "stage_b_entry": {
                "EVIDENCE_PRESENT": "PERMIT_STAGE_B",
                "NO_EVIDENCE": "STOP",
                "UNCERTAIN": "ABSTAIN",
            },
        },
        "schema": SCHEMA_PROMOTION,
        "state": dict(state),
    }
    payload["STAGE_A_PROMOTION_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in payload.items()
                if k != "STAGE_A_PROMOTION_RECEIPT_SHA256"
            }
        )
    )
    return payload
