"""RETRY_PROMOTE_STAGE_A_IDENT_FILTERED_FACTORIZED_CANDIDATE.

Promotes the REPRO-001 complete checkpoint f2b00c5d… to STAGE_A_BEST.
Never promotes the historical incomplete packaging artifact 8b2de447….
Does not retrain, alter thresholds/V1R2, score spent reserve, or move
MODEL_WIDE_BEST.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .classification_v5_stage_a import (
    BEST_SHA,
    EVIDENCE_LABELS,
    canonical_json,
    sha256_text,
)
from .classification_v5_stage_a_factorized_objective import (
    OBJECTIVE_ID,
    OBJECTIVE_RECEIPT_SHA256_PIN,
    POSSIBLE_EVIDENCE_STATUS as OBJECTIVE_POSSIBLE_EVIDENCE_STATUS,
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
    AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
    EXPLICIT_LIMITATIONS,
)
from .classification_v5_stage_a_ident_filtered_promote import (
    CANONICAL_FORWARD_SCHEMA,
    CANONICAL_INFERENCE_POLICY,
    CANONICAL_LOAD_SEQUENCE,
    CANONICAL_RELATION_THRESHOLD,
    CANONICAL_RESOLVABILITY_THRESHOLD,
    DISPLAY_METRICS,
    EXPECTED_METRICS,
    FLAT_ALLOWED_USES,
    FLAT_RUNTIME_STATUS,
    METRIC_ABS_TOL,
    POSSIBLE_EVIDENCE_STATUS,
    PROVENANCE_NOTE,
    SCHEMA_STAGE_A_BEST,
    SUPERSEDED_STAGE_A_BEST_STATUS,
    TWO_STAGE_RUNTIME_STATUS,
    choose_promotion_state,
    decide_canonical_stage_a,
    deprecated_path_status,
    may_invoke_stage_b,
    metric_parity,
    post_promotion_replay_check,
    short_atom_diagnostics,
    stage_b_entry_from_stage_a,
    utc_now_iso,
    verify_canonical_overlay,
    verify_factorized_architecture,
)
from .classification_v5_stage_a_ident_filtered_repro_authorize import (
    CHECKPOINT_REPAIR_RECEIPT_SHA256,
    EXPERIMENT_ID,
    ORIGINAL_RUN_RECEIPT_SHA256,
    ORIGINAL_SELECTED_ENCODER_ONLY_SHA256,
    PARENT_EXPERIMENT,
    REPRODUCTION_REASON,
)
from .classification_v5_stage_a_two_stage_generalization import (
    PARENT_STAGE_A_BEST_SHA,
    SPENT_RESERVE,
    SPENT_RESERVE_STATUS,
)
from .save_pretrained import FACTORIZED_HEAD_NAMES

PROMOTE_RULE = "RETRY_PROMOTE_STAGE_A_IDENT_FILTERED_FACTORIZED_CANDIDATE"
SCHEMA_PROMOTION = (
    "hyperlex.classification.v5.stage_a_ident_filtered_factorized_repro_promotion.v1"
)
NEXT_ACTION_ON_PASS = (
    "FREEZE_V5_STAGE_A_CANONICAL_AND_UPDATE_DOWNSTREAM_PROVENANCE"
)

ORIGINAL_EXPERIMENT_ID = PARENT_EXPERIMENT
REPRODUCTION_CLASSIFICATION_TARGET = "SCIENTIFICALLY_EQUIVALENT_REPRODUCTION"
AUTHORIZED_AUTH_RECEIPT_SHA256 = (
    "09f3d456961aaa9027ff35ac653f3d6aeee627ceee1eb705fcd83dc9b9c3205b"
)
AUTHORIZED_TRAINING_CONFIG_SHA256 = (
    "731c0b260fb5f6966c47d1700d522c42aad8126b6be2f482b078eb6c8ab8325e"
)

STAGE_A_BEST_SHA256 = (
    "f2b00c5dfeb087288fc1686c901fbc8b52a8ba7a7b51cb83ff038656f93617fa"
)
STAGE_A_BEST_EPOCH = 11
EXPECTED_SELECTION_SCORE = 0.9672661029515868
SELECTION_SCORE_DISPLAY = 0.9673
PREVIOUS_STAGE_A_BEST_SHA256 = PARENT_STAGE_A_BEST_SHA  # cd2829c1…
MODEL_WIDE_BEST_SHA256 = BEST_SHA
PARENT_ENCODER_BEST_SHA256 = BEST_SHA
assert PARENT_ENCODER_BEST_SHA256 == MODEL_WIDE_BEST_SHA256

EXPECTED_RUN_RECEIPT_SHA256 = (
    "8b8585a8637176a64adf9ce6cff2a076fd4bf938070aef02203fa46978e20ed1"
)
ORIGINAL_SETTLED_RECEIPT_SHA256 = ORIGINAL_RUN_RECEIPT_SHA256
REPAIR_FAILURE_RECEIPT_SHA256 = CHECKPOINT_REPAIR_RECEIPT_SHA256

INCOMPLETE_HISTORICAL_CHECKPOINT_SHA256 = ORIGINAL_SELECTED_ENCODER_ONLY_SHA256
HISTORICAL_ARTIFACT_STATUS = {
    "checkpoint_sha256": INCOMPLETE_HISTORICAL_CHECKPOINT_SHA256,
    "roles": [
        "SCIENTIFIC_SELECTED_STATE_REFERENCE",
        "NON_PROMOTABLE_PACKAGING_ARTIFACT",
        "SUPERSEDED_BY_REPRODUCTION_CHECKPOINT",
    ],
    "may_become_STAGE_A_BEST": False,
    "superseded_by": STAGE_A_BEST_SHA256,
}

REQUIRED_FACTORIZED_HEAD_KEYS = (
    "relation_head.weight",
    "relation_head.bias",
    "resolvability_head.weight",
    "resolvability_head.bias",
)
EXPECTED_N_KEYS = 16

CENTRAL_SCIENTIFIC_CONCLUSION = (
    "Gold/input identifiability repair, not architecture escalation, "
    "resolved the dominant Stage-A failure."
)

LINEAGE = (
    "original scientific experiment",
    "original SETTLED_PASS",
    "packaging failure",
    "repair impossible",
    "authorized reproduction",
    "scientifically equivalent SETTLED_PASS",
    "complete promotion-loadable checkpoint",
)


def _selection_score(train_receipt: Mapping[str, Any]) -> float:
    for key in (
        "selection_score",
        "SELECTED_SCORE",
        "selected_score",
        "best_selection_score",
    ):
        if train_receipt.get(key) is not None:
            return float(train_receipt[key])
    restored = train_receipt.get("restored") or {}
    if restored.get("selection_score") is not None:
        return float(restored["selection_score"])
    metrics = train_receipt.get("selected_metrics") or {}
    if metrics.get("selection_score") is not None:
        return float(metrics["selection_score"])
    return float("nan")


def verify_head_completeness(stage_a_tensor_keys: Sequence[str]) -> dict[str, Any]:
    keys = [str(k) for k in stage_a_tensor_keys]
    key_set = set(keys)
    present = {k: k in key_set for k in REQUIRED_FACTORIZED_HEAD_KEYS}
    arch = verify_factorized_architecture(keys)
    n_keys = len(keys)
    ok = (
        all(present.values())
        and bool(arch.get("pass"))
        and n_keys == EXPECTED_N_KEYS
    )
    return {
        "factorized_heads_cold_loadable": ok,
        "n_keys": n_keys,
        "expected_n_keys": EXPECTED_N_KEYS,
        "required_keys_present": present,
        "factorized_head_names": list(FACTORIZED_HEAD_NAMES),
        "architecture": arch,
        "pass": ok,
    }


def preflight_promotion(
    *,
    train_receipt: Mapping[str, Any],
    selected_checkpoint_sha256: str,
    model_wide_best_sha256: str,
    current_stage_a_best_sha256: str,
    dataset_sha256: str,
    annotation_sha256: str,
    exclusion_manifest_sha256: str,
    v1r2_mutated: bool,
    stage_a_tensor_keys: Sequence[str] | None = None,
) -> dict[str, Any]:
    gates = train_receipt.get("acceptance_gates") or {}
    thr = train_receipt.get("selected_thresholds") or {}
    score = _selection_score(train_receipt)

    def _gate_value(name: str) -> float:
        return float((gates.get(name) or {}).get("value") or -1.0)

    head_check = None
    if stage_a_tensor_keys is not None:
        head_check = verify_head_completeness(stage_a_tensor_keys)

    checks = {
        "scientific_settled_pass": train_receipt.get("SCIENTIFIC_RESULT")
        == "SETTLED_PASS",
        "reproduction_classification": train_receipt.get("REPRODUCTION_CLASSIFICATION")
        == REPRODUCTION_CLASSIFICATION_TARGET,
        "experiment": train_receipt.get("EXPERIMENT_ID") == EXPERIMENT_ID,
        "parent_experiment": train_receipt.get("PARENT_EXPERIMENT")
        in (PARENT_EXPERIMENT, ORIGINAL_EXPERIMENT_ID),
        "surface_sha": dataset_sha256 == V1R2_DATASET_SHA256_PIN
        and train_receipt.get("DATASET_SHA256") == V1R2_DATASET_SHA256_PIN,
        "annotation_sha": annotation_sha256 == V1R2_ANNOTATION_SHA256_PIN
        and train_receipt.get("ANNOTATION_SHA256") == V1R2_ANNOTATION_SHA256_PIN,
        "exclusion_manifest_sha": exclusion_manifest_sha256
        == V1R2_EXCLUSION_MANIFEST_SHA256_PIN
        and train_receipt.get("EXCLUSION_MANIFEST_SHA256")
        == V1R2_EXCLUSION_MANIFEST_SHA256_PIN,
        "authorization_receipt": train_receipt.get("AUTHORIZATION_RECEIPT_SHA256")
        == AUTHORIZED_AUTH_RECEIPT_SHA256,
        "training_config_sha": train_receipt.get("TRAINING_CONFIG_SHA256")
        == AUTHORIZED_TRAINING_CONFIG_SHA256,
        "class_weight_artifact_sha": train_receipt.get("CLASS_WEIGHT_ARTIFACT_SHA256")
        == AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
        "selected_complete_checkpoint": selected_checkpoint_sha256
        == STAGE_A_BEST_SHA256
        and train_receipt.get("SELECTED_CHECKPOINT_SHA256") == STAGE_A_BEST_SHA256
        and (
            train_receipt.get("SELECTED_COMPLETE_CHECKPOINT_SHA256") in (None, STAGE_A_BEST_SHA256)
        ),
        "not_incomplete_historical": selected_checkpoint_sha256
        != INCOMPLETE_HISTORICAL_CHECKPOINT_SHA256,
        "selected_epoch": int(
            train_receipt.get("restored_epoch")
            or train_receipt.get("selected_epoch")
            or -1
        )
        == STAGE_A_BEST_EPOCH,
        "selection_score": abs(score - EXPECTED_SELECTION_SCORE) <= METRIC_ABS_TOL
        or abs(score - SELECTION_SCORE_DISPLAY) < 5e-4,
        "relation_threshold": float(thr.get("relation_threshold") or -1.0)
        == CANONICAL_RELATION_THRESHOLD,
        "resolvability_threshold": float(thr.get("resolvability_threshold") or -1.0)
        == CANONICAL_RESOLVABILITY_THRESHOLD,
        "false_entry_gate": _gate_value("false_evidence_entry_rate_on_none") <= 0.05
        and bool((gates.get("false_evidence_entry_rate_on_none") or {}).get("pass")),
        "present_recall_gate": _gate_value("EVIDENCE_PRESENT_recall") >= 0.70
        and bool((gates.get("EVIDENCE_PRESENT_recall") or {}).get("pass")),
        "none_recall_gate": _gate_value("NO_EVIDENCE_recall") >= 0.90
        and bool((gates.get("NO_EVIDENCE_recall") or {}).get("pass")),
        "v1r2_unchanged": v1r2_mutated is False
        and train_receipt.get("V1R2_MUTATED") is False,
        "spent_reserve_status": train_receipt.get("RESERVE") == SPENT_RESERVE_STATUS
        or train_receipt.get("SPENT_RESERVE") == SPENT_RESERVE,
        "model_wide_best": model_wide_best_sha256 == MODEL_WIDE_BEST_SHA256,
        "current_stage_a_best": current_stage_a_best_sha256
        == PREVIOUS_STAGE_A_BEST_SHA256,
        "run_receipt": train_receipt.get("RUN_RECEIPT_SHA256")
        == EXPECTED_RUN_RECEIPT_SHA256,
        "objective": train_receipt.get("OBJECTIVE_ID") == OBJECTIVE_ID,
        "factorized_heads_present": (
            True if head_check is None else bool(head_check.get("pass"))
        ),
    }
    return {
        "checks": checks,
        "head_completeness": head_check,
        "pass": all(checks.values()),
        "result": "PASS" if all(checks.values()) else "PROMOTION_INVALID",
        "selection_score_observed": score,
    }


def canonical_load_contract() -> dict[str, Any]:
    return {
        "architecture": OBJECTIVE_ID,
        "fail_closed_if": [
            "parent_BEST_sha_mismatch",
            "stage_a_overlay_name_or_shape_mismatch",
            "missing_relation_or_resolvability_head",
            "gate1_or_gate2_head_loaded_as_canonical",
            "flat_evidence_head_loaded_as_canonical",
            "incomplete_historical_8b2de447_promoted",
        ],
        "forward_schema": CANONICAL_FORWARD_SCHEMA,
        "relation_threshold": CANONICAL_RELATION_THRESHOLD,
        "resolvability_threshold": CANONICAL_RESOLVABILITY_THRESHOLD,
        "parent_encoder_best": PARENT_ENCODER_BEST_SHA256,
        "runtime_threshold_search": False,
        "sequence": list(CANONICAL_LOAD_SEQUENCE),
        "stage_a_best": STAGE_A_BEST_SHA256,
        "stage_a_parent_model_wide_best": PARENT_ENCODER_BEST_SHA256,
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
        "architecture": OBJECTIVE_ID,
        "auto_relabel": False,
        "checkpoint_sha256": STAGE_A_BEST_SHA256,
        "code_revision": code_revision,
        "component": "STAGE_A",
        "context_dependent_definitive_gold_excluded": True,
        "experiment_id": EXPERIMENT_ID,
        "factorized_heads_cold_loadable": True,
        "forward_schema": CANONICAL_FORWARD_SCHEMA,
        "gold_identifiability_contract_id": CONTRACT_ID,
        "gold_identifiability_contract_receipt_sha256": CONTRACT_RECEIPT_SHA256_PIN,
        "identifiability_filter_receipt_sha256": FILTER_RECEIPT_SHA256_PIN,
        "load_sequence": list(CANONICAL_LOAD_SEQUENCE),
        "model_input": list(MODEL_INPUT),
        "model_wide_BEST": MODEL_WIDE_BEST_SHA256,
        "model_wide_BEST_mutated": False,
        "n_keys": EXPECTED_N_KEYS,
        "objective_id": OBJECTIVE_ID,
        "objective_receipt_sha256": OBJECTIVE_RECEIPT_SHA256_PIN,
        "original_experiment_id": ORIGINAL_EXPERIMENT_ID,
        "parent_encoder_best": PARENT_ENCODER_BEST_SHA256,
        "parent_model_wide_best": PARENT_ENCODER_BEST_SHA256,
        "previous_STAGE_A_BEST": previous_stage_a_best,
        "promoted_at": promoted_at or utc_now_iso(),
        "promotion_rule": PROMOTE_RULE,
        "relation_threshold": CANONICAL_RELATION_THRESHOLD,
        "reproduction_classification": REPRODUCTION_CLASSIFICATION_TARGET,
        "resolvability_threshold": CANONICAL_RESOLVABILITY_THRESHOLD,
        "schema": SCHEMA_STAGE_A_BEST,
        "selection_score": EXPECTED_SELECTION_SCORE,
        "semantic_outputs": list(EVIDENCE_LABELS),
        "stage_a_parent_model_wide_best": PARENT_ENCODER_BEST_SHA256,
        "surface_id": SURFACE_ID,
        "surface_dataset_sha256": V1R2_DATASET_SHA256_PIN,
        "weights_path": weights_path,
    }


def round_trip_logit_parity(
    *,
    decisions_a: Sequence[str],
    decisions_b: Sequence[str],
    logits_a: Sequence[Sequence[float]] | None = None,
    logits_b: Sequence[Sequence[float]] | None = None,
    abs_tol: float = 1e-6,
) -> dict[str, Any]:
    if len(decisions_a) != len(decisions_b):
        return {
            "pass": False,
            "decision_mismatch_count": -1,
            "reason": "length_mismatch",
        }
    mismatches = sum(
        1 for a, b in zip(decisions_a, decisions_b) if str(a) != str(b)
    )
    logit_ok = True
    max_abs = 0.0
    if logits_a is not None and logits_b is not None:
        if len(logits_a) != len(logits_b):
            logit_ok = False
        else:
            for la, lb in zip(logits_a, logits_b):
                for x, y in zip(la, lb):
                    delta = abs(float(x) - float(y))
                    if delta > max_abs:
                        max_abs = delta
                    if delta > abs_tol:
                        logit_ok = False
    return {
        "pass": mismatches == 0 and logit_ok,
        "decision_mismatch_count": mismatches,
        "logit_abs_tol": abs_tol,
        "logit_max_abs_delta": max_abs,
        "logit_parity_pass": logit_ok,
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
    head_completeness: Mapping[str, Any] | None = None,
    round_trip: Mapping[str, Any] | None = None,
    factorized_head_manifest_hashes: Mapping[str, str] | None = None,
    checkpoint_tensor_manifest_hash: str | None = None,
) -> dict[str, Any]:
    replay_ok = bool(post_replay.get("pass"))
    if round_trip is not None:
        replay_ok = replay_ok and bool(round_trip.get("pass"))
    state = choose_promotion_state(
        preflight_pass=bool(preflight.get("pass")),
        overlay_pass=bool(overlay.get("pass")),
        post_replay_pass=replay_ok,
    )
    known_limitations = {
        "DOMAIN_IRRELEVANT_GENERALIZATION": "NOT_ESTABLISHED",
        "SHORT_ATOM_POSITIVE_GENERALIZATION": "LOW_SUPPORT",
        "CONTEXT_DEPENDENT_GOLD": "OUTSIDE_CURRENT_TEXT_ONLY_STAGE_A_CONTRACT",
        "provenance_note": PROVENANCE_NOTE,
        "central_scientific_conclusion": CENTRAL_SCIENTIFIC_CONCLUSION,
    }
    payload = {
        "ANNOTATION_SHA256": V1R2_ANNOTATION_SHA256_PIN,
        "AUTHORIZATION_RECEIPT_SHA256": AUTHORIZED_AUTH_RECEIPT_SHA256,
        "BEST_MUTATED": False,
        "CHECKPOINT_REPAIR_RECEIPT_SHA256": REPAIR_FAILURE_RECEIPT_SHA256,
        "CLASS_WEIGHT_ARTIFACT_SHA256": AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
        "CONTRACT_ID": CONTRACT_ID,
        "CONTRACT_RECEIPT_SHA256": CONTRACT_RECEIPT_SHA256_PIN,
        "DATASET_SHA256": V1R2_DATASET_SHA256_PIN,
        "EXCLUSION_MANIFEST_SHA256": V1R2_EXCLUSION_MANIFEST_SHA256_PIN,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "FILTER_RECEIPT_SHA256": FILTER_RECEIPT_SHA256_PIN,
        "HISTORICAL_INCOMPLETE_ARTIFACT": dict(HISTORICAL_ARTIFACT_STATUS),
        "LINEAGE": list(LINEAGE),
        "MODEL_INPUT": list(MODEL_INPUT),
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "NEXT_ACTION": (
            NEXT_ACTION_ON_PASS if state["applied"] else "PROMOTION_INVALID"
        ),
        "OBJECTIVE_ID": OBJECTIVE_ID,
        "OBJECTIVE_RECEIPT_SHA256": OBJECTIVE_RECEIPT_SHA256_PIN,
        "ORIGINAL_EXPERIMENT_ID": ORIGINAL_EXPERIMENT_ID,
        "ORIGINAL_RESULT_RECEIPT": ORIGINAL_SETTLED_RECEIPT_SHA256,
        "ORIGINAL_SETTLED_RESULT_RECEIPT_SHA256": ORIGINAL_SETTLED_RECEIPT_SHA256,
        "PARENT_ENCODER_BEST": PARENT_ENCODER_BEST_SHA256,
        "PARENT_EXPERIMENT": PARENT_EXPERIMENT,
        "POSSIBLE_EVIDENCE": POSSIBLE_EVIDENCE_STATUS,
        "PROMOTION_INVALID": state["PROMOTION_INVALID"],
        "PROMOTION_LOADABLE": bool(state["applied"]),
        "PROMOTE_RULE": PROMOTE_RULE,
        "REPAIR_FAILURE_RECEIPT_SHA256": REPAIR_FAILURE_RECEIPT_SHA256,
        "REPRODUCTION_CLASSIFICATION": REPRODUCTION_CLASSIFICATION_TARGET,
        "REPRODUCTION_REASON": REPRODUCTION_REASON,
        "REPRO_RESULT_RECEIPT": EXPECTED_RUN_RECEIPT_SHA256,
        "RESERVE_CONSUMED": False,
        "RUN_RECEIPT_SHA256": EXPECTED_RUN_RECEIPT_SHA256,
        "SELECTED_CHECKPOINT_SHA256": STAGE_A_BEST_SHA256,
        "SELECTED_COMPLETE_CHECKPOINT_SHA256": STAGE_A_BEST_SHA256,
        "SELECTED_EPOCH": STAGE_A_BEST_EPOCH,
        "SELECTION_SCORE": EXPECTED_SELECTION_SCORE,
        "SPENT_RESERVE": SPENT_RESERVE,
        "SPENT_RESERVE_STATUS": SPENT_RESERVE_STATUS,
        "STAGE_A_BEST": (
            STAGE_A_BEST_SHA256 if state["applied"] else previous_stage_a_best
        ),
        "STAGE_A_PROMOTION": state["STAGE_A_PROMOTION"],
        "SURFACE_ID": SURFACE_ID,
        "TRAIN": False,
        "TRAINING_CONFIG_SHA256": AUTHORIZED_TRAINING_CONFIG_SHA256,
        "V1R2_MUTATED": False,
        "auto_relabel": False,
        "canonical_forward_schema": CANONICAL_FORWARD_SCHEMA,
        "canonical_inference_policy": CANONICAL_INFERENCE_POLICY,
        "canonical_load_path": canonical_load_contract(),
        "canonical_thresholds": {
            "relation_threshold": CANONICAL_RELATION_THRESHOLD,
            "resolvability_threshold": CANONICAL_RESOLVABILITY_THRESHOLD,
        },
        "central_scientific_conclusion": CENTRAL_SCIENTIFIC_CONCLUSION,
        "checkpoint_tensor_manifest_hash": checkpoint_tensor_manifest_hash,
        "code_revision": code_revision,
        "context_dependent_definitive_gold_excluded": True,
        "deprecated_paths": deprecated_path_status(),
        "display_metrics": dict(DISPLAY_METRICS),
        "explicit_limitations": dict(EXPLICIT_LIMITATIONS),
        "factorized_head_manifest_hashes": dict(factorized_head_manifest_hashes or {}),
        "head_completeness": dict(head_completeness or {}),
        "known_limitations": known_limitations,
        "overlay_verification": dict(overlay),
        "pointer": dict(pointer) if state["applied"] else None,
        "post_promotion_replay": dict(post_replay),
        "preflight": dict(preflight),
        "previous_STAGE_A_BEST": previous_stage_a_best,
        "promoted_at": promoted_at or utc_now_iso(),
        "provenance_note": PROVENANCE_NOTE,
        "round_trip_logit_parity": dict(round_trip or {}),
        "runtime_adapter": {
            "decide_canonical_stage_a": (
                "decide_stage_a(p_relation,p_resolvable;"
                "thr=0.60/0.75)"
            ),
            "semantic_outputs": list(EVIDENCE_LABELS),
            "internal_fields": [
                "p_relation",
                "p_resolvable",
                "relation_threshold",
                "resolvability_threshold",
            ],
            "stage_b_entry": {
                "EVIDENCE_PRESENT": "PERMIT_STAGE_B",
                "NO_EVIDENCE": "STOP",
                "UNCERTAIN": "ABSTAIN",
            },
            "stage_b_index_mutated": False,
            "stage_b_score_floor_mutated": False,
            "stage_b_margin_floor_mutated": False,
            "stage_b_family_ontology_mutated": False,
            "stage_b_parent_pin_update": "DEFERRED_TO_DOWNSTREAM_PROVENANCE",
        },
        "schema": SCHEMA_PROMOTION,
        "short_atom_diagnostics": (post_replay or {}).get("short_atom_diagnostics"),
        "stage_a_parent_model_wide_best": PARENT_ENCODER_BEST_SHA256,
        "state": dict(state),
    }
    # Preserve POSSIBLE_EVIDENCE deprecation marker from objective.
    assert OBJECTIVE_POSSIBLE_EVIDENCE_STATUS.startswith("DEPRECATED")
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


__all__ = [
    "CANONICAL_RELATION_THRESHOLD",
    "CANONICAL_RESOLVABILITY_THRESHOLD",
    "EXPECTED_METRICS",
    "INCOMPLETE_HISTORICAL_CHECKPOINT_SHA256",
    "MODEL_WIDE_BEST_SHA256",
    "PREVIOUS_STAGE_A_BEST_SHA256",
    "PROMOTE_RULE",
    "STAGE_A_BEST_SHA256",
    "build_promotion_receipt",
    "build_stage_a_best_pointer",
    "canonical_load_contract",
    "decide_canonical_stage_a",
    "may_invoke_stage_b",
    "metric_parity",
    "post_promotion_replay_check",
    "preflight_promotion",
    "round_trip_logit_parity",
    "short_atom_diagnostics",
    "stage_b_entry_from_stage_a",
    "utc_now_iso",
    "verify_canonical_overlay",
    "verify_factorized_architecture",
    "verify_head_completeness",
]
