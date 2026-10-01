"""REPAIR_IDENT_FILTERED_FACTORIZED_CHECKPOINT_SERIALIZATION.

Artifact-repair only. Reconstructs a promotable factorized Stage-A checkpoint
from exact selected-epoch head tensors when retained; otherwise fails closed
as REPAIR_NOT_POSSIBLE_WITHOUT_RETRAIN. Does not retrain, move BEST, or alter
V1R2 / Stage B / thresholds.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .classification_v5_stage_a import BEST_SHA, canonical_json, sha256_text
from .classification_v5_stage_a_factorized_objective import OBJECTIVE_ID
from .classification_v5_stage_a_gold_identifiability_filter import (
    V1R2_ANNOTATION_SHA256_PIN,
    V1R2_DATASET_SHA256_PIN,
    V1R2_EXCLUSION_MANIFEST_SHA256_PIN,
)
from .classification_v5_stage_a_ident_filtered_authorize import (
    AUTHORIZED_AUTH_RECEIPT_SHA256,
    AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
    AUTHORIZED_TRAINING_CONFIG_SHA256,
    EXPERIMENT_ID,
)
from .classification_v5_stage_a_ident_filtered_promote import (
    PREVIOUS_STAGE_A_BEST_SHA256,
    STAGE_A_BEST_SHA256 as INCOMPLETE_SELECTED_CHECKPOINT_SHA256,
    verify_factorized_architecture,
)
from .classification_v5_stage_a_two_stage_generalization import (
    SPENT_RESERVE,
    SPENT_RESERVE_STATUS,
)
from .layout import HIDDEN
from .save_pretrained import (
    FACTORIZED_HEAD_NAMES,
    flatten_weight_tensors,
    require_factorized_heads_in_flat,
    split_weight_tensors,
)

REPAIR_RULE = "REPAIR_IDENT_FILTERED_FACTORIZED_CHECKPOINT_SERIALIZATION"
SCHEMA_REPAIR = (
    "hyperlex.classification.v5."
    "stage_a_ident_filtered_factorized_checkpoint_repair.v1"
)

SELECTED_EPOCH = 11
TRAINING_RESULT_RECEIPT_SHA256 = (
    "4a7d565ca607234c604bcec40acab33e3cbecc4da6e4adc86a0b2b79bb091a4b"
)
PROMOTION_INVALID_RECEIPT_SHA256 = (
    "1123d70dec32b82709a9c44225471a90fd358d985ecc55751f22d5a56696829e"
)

INCOMPLETE_CHECKPOINT_STATUS = "SCIENTIFIC_SELECTED_STATE_REFERENCE"
INCOMPLETE_CHECKPOINT_PROMOTABILITY = "NON_PROMOTABLE_PACKAGING_ARTIFACT"

REQUIRED_HEAD_TENSORS = (
    "relation_head.weight",
    "relation_head.bias",
    "resolvability_head.weight",
    "resolvability_head.bias",
)

ALLOWED_HEAD_SOURCES = (
    "A_retained_selected_epoch_trainer_state_before_flattening",
    "B_retained_in_memory_or_export_artifact_with_exact_heads",
    "C_deterministic_selected_epoch_state_artifact_with_exact_heads",
)

FORBIDDEN_HEAD_SOURCES = (
    "fresh_xavier_initialization",
    "final_epoch_heads_substituted_for_selected_epoch",
    "heads_from_another_experiment",
    "retrained_heads",
    "reconstructed_weights_from_metrics_or_logits",
)

NEXT_ACTION_ON_PASS = "RETRY_PROMOTE_STAGE_A_IDENT_FILTERED_FACTORIZED_CANDIDATE"
NEXT_ACTION_ON_FAIL = "AUTHORIZE_REPRODUCE_IDENT_FILTERED_FACTORIZED_TRAIN"


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def classify_tensor_keys(keys: Sequence[str]) -> dict[str, Any]:
    key_set = set(str(k) for k in keys)
    present_heads = [name for name in REQUIRED_HEAD_TENSORS if name in key_set]
    missing_heads = [name for name in REQUIRED_HEAD_TENSORS if name not in key_set]
    return {
        "n_keys": len(key_set),
        "n_encoder_keys": sum(1 for k in key_set if k.startswith("encoder.")),
        "present_required_heads": present_heads,
        "missing_required_heads": missing_heads,
        "has_all_required_heads": not missing_heads,
        "architecture": verify_factorized_architecture(sorted(key_set)),
    }


def audit_candidate_sources(
    *,
    artifacts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Inspect candidate weight artifacts for exact factorized heads.

    Each artifact mapping may include:
      path, sha256, keys (list[str]), role, epoch
    """
    inspected = []
    recoverable = []
    for art in artifacts:
        keys = list(art.get("keys") or [])
        classification = classify_tensor_keys(keys)
        row = {
            "path": art.get("path"),
            "role": art.get("role"),
            "epoch": art.get("epoch"),
            "sha256": art.get("sha256"),
            "classification": classification,
            "usable_as_selected_head_source": bool(
                classification["has_all_required_heads"]
            ),
        }
        inspected.append(row)
        if row["usable_as_selected_head_source"]:
            recoverable.append(row)

    # Prefer epoch-11 explicit selected sources.
    authoritative = None
    for row in recoverable:
        if int(row.get("epoch") or -1) == SELECTED_EPOCH:
            authoritative = row
            break
    if authoritative is None and recoverable:
        authoritative = recoverable[0]

    return {
        "allowed_source_classes": list(ALLOWED_HEAD_SOURCES),
        "forbidden_source_classes": list(FORBIDDEN_HEAD_SOURCES),
        "inspected": inspected,
        "recoverable_sources": recoverable,
        "authoritative_selected_head_source": authoritative,
        "exact_selected_epoch_heads_available": authoritative is not None
        and int(authoritative.get("epoch") or -1) == SELECTED_EPOCH,
    }


def verify_selected_epoch_identity(
    *,
    experiment_id: str,
    selected_epoch: int,
    selected_encoder_sha256: str,
    dataset_sha256: str,
    training_config_sha256: str,
    authorization_sha256: str,
) -> dict[str, Any]:
    checks = {
        "experiment_id": experiment_id == EXPERIMENT_ID,
        "selected_epoch": int(selected_epoch) == SELECTED_EPOCH,
        "selected_encoder_sha": selected_encoder_sha256
        == INCOMPLETE_SELECTED_CHECKPOINT_SHA256,
        "dataset": dataset_sha256 == V1R2_DATASET_SHA256_PIN,
        "training_config": training_config_sha256
        == AUTHORIZED_TRAINING_CONFIG_SHA256,
        "authorization": authorization_sha256 == AUTHORIZED_AUTH_RECEIPT_SHA256,
    }
    return {"checks": checks, "pass": all(checks.values())}


def serialization_regression_report() -> dict[str, Any]:
    """Pure unit-level checks that factorized heads survive flatten/split."""
    state = {
        "encoder": {
            "encoder.layers.20.weight": [1.0],
            "encoder.layers.21.weight": [2.0],
        },
        "relation_head": {
            "weight": [[0.1] * HIDDEN, [0.2] * HIDDEN],
            "bias": [0.3, 0.4],
        },
        "resolvability_head": {
            "weight": [[0.5] * HIDDEN, [0.6] * HIDDEN],
            "bias": [0.7, 0.8],
        },
    }
    flat = flatten_weight_tensors(state)
    require = require_factorized_heads_in_flat(flat)
    split = split_weight_tensors(flat)
    incomplete = flatten_weight_tensors(
        {
            "encoder": {"encoder.layers.20.weight": [1.0]},
            # heads intentionally omitted
        }
    )
    incomplete_req = require_factorized_heads_in_flat(incomplete)
    wrong_shape = flatten_weight_tensors(
        {
            "encoder": {"encoder.layers.20.weight": [1.0]},
            "relation_head": {"weight": [[0.1, 0.2], [0.3, 0.4]], "bias": [0.0, 0.0]},
            "resolvability_head": {
                "weight": [[0.5] * HIDDEN, [0.6] * HIDDEN],
                "bias": [0.7, 0.8],
            },
        }
    )
    wrong_shape_req = require_factorized_heads_in_flat(wrong_shape)
    historical_incomplete_keys = [
        f"encoder.layers.{i}.weight" for i in range(12)
    ]  # stand-in encoder-only keyset
    historical = classify_tensor_keys(historical_incomplete_keys)
    return {
        "factorized_head_names_whitelisted": list(FACTORIZED_HEAD_NAMES),
        "flatten_preserves_relation_head": "relation_head.weight" in flat
        and "relation_head.bias" in flat,
        "flatten_preserves_resolvability_head": "resolvability_head.weight" in flat
        and "resolvability_head.bias" in flat,
        "require_factorized_heads_pass_on_complete": require["pass"],
        "require_factorized_heads_fail_on_incomplete": incomplete_req["pass"] is False,
        "require_factorized_heads_fail_on_wrong_shape": wrong_shape_req["pass"] is False,
        "split_roundtrip_relation_bias": split["relation_head"]["bias"]
        == state["relation_head"]["bias"],
        "split_roundtrip_resolvability_weight": split["resolvability_head"]["weight"]
        == state["resolvability_head"]["weight"],
        "historical_incomplete_rejected": historical["has_all_required_heads"] is False,
        "pass": all(
            [
                "relation_head.weight" in flat,
                "resolvability_head.weight" in flat,
                require["pass"],
                incomplete_req["pass"] is False,
                wrong_shape_req["pass"] is False,
                historical["has_all_required_heads"] is False,
            ]
        ),
    }


def build_repair_receipt(
    *,
    source_audit: Mapping[str, Any],
    identity: Mapping[str, Any],
    serialization_tests: Mapping[str, Any],
    code_revision: str,
    repaired_at: str | None = None,
    repaired_checkpoint_sha256: str | None = None,
    tensor_parity: Mapping[str, Any] | None = None,
    cold_load: Mapping[str, Any] | None = None,
    validation_replay: Mapping[str, Any] | None = None,
    logit_parity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    heads_available = bool(source_audit.get("exact_selected_epoch_heads_available"))
    identity_ok = bool(identity.get("pass"))
    serialization_ok = bool(serialization_tests.get("pass"))

    if not heads_available:
        repair_status = "REPAIR_NOT_POSSIBLE_WITHOUT_RETRAIN"
        checkpoint_repair = "FAIL"
        promotion_loadable = False
        reason = "exact_selected_epoch_head_tensors_not_retained"
    elif not identity_ok:
        repair_status = "CHECKPOINT_REPAIR_INVALID"
        checkpoint_repair = "FAIL"
        promotion_loadable = False
        reason = "selected_epoch_identity_mismatch"
    elif repaired_checkpoint_sha256 and tensor_parity and cold_load and validation_replay:
        parity_ok = bool((tensor_parity or {}).get("pass"))
        cold_ok = bool((cold_load or {}).get("pass"))
        replay_ok = bool((validation_replay or {}).get("pass"))
        logit_ok = True if logit_parity is None else bool(logit_parity.get("pass"))
        if parity_ok and cold_ok and replay_ok and logit_ok and serialization_ok:
            repair_status = "PASS"
            checkpoint_repair = "PASS"
            promotion_loadable = True
            reason = "ok"
        else:
            repair_status = "CHECKPOINT_REPAIR_INVALID"
            checkpoint_repair = "FAIL"
            promotion_loadable = False
            reason = "parity_or_cold_load_or_replay_failed"
    else:
        repair_status = "REPAIR_NOT_POSSIBLE_WITHOUT_RETRAIN"
        checkpoint_repair = "FAIL"
        promotion_loadable = False
        reason = "reconstruction_not_attempted_without_authoritative_heads"

    payload = {
        "ANNOTATION_SHA256": V1R2_ANNOTATION_SHA256_PIN,
        "AUTHORIZATION_RECEIPT_SHA256": AUTHORIZED_AUTH_RECEIPT_SHA256,
        "CHECKPOINT_REPAIR": checkpoint_repair,
        "CLASS_WEIGHT_ARTIFACT_SHA256": AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
        "DATASET_SHA256": V1R2_DATASET_SHA256_PIN,
        "EXCLUSION_MANIFEST_SHA256": V1R2_EXCLUSION_MANIFEST_SHA256_PIN,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "INCOMPLETE_SELECTED_CHECKPOINT_SHA256": INCOMPLETE_SELECTED_CHECKPOINT_SHA256,
        "MODEL_WIDE_BEST": BEST_SHA,
        "MODEL_WIDE_BEST_MUTATED": False,
        "NEXT_ACTION": (
            NEXT_ACTION_ON_PASS if promotion_loadable else NEXT_ACTION_ON_FAIL
        ),
        "OBJECTIVE_ID": OBJECTIVE_ID,
        "PROMOTION_INVALID_RECEIPT_SHA256": PROMOTION_INVALID_RECEIPT_SHA256,
        "PROMOTION_LOADABLE": promotion_loadable,
        "REPAIR_RULE": REPAIR_RULE,
        "REPAIR_STATUS": repair_status,
        "REPAIRED_STAGE_A_CHECKPOINT_SHA256": repaired_checkpoint_sha256,
        "RESERVE_CONSUMED": False,
        "SCIENTIFIC_RESULT": "SETTLED_PASS",
        "SCIENTIFIC_RESULT_SOURCE": "original settled run",
        "SELECTED_EPOCH": SELECTED_EPOCH,
        "SPENT_RESERVE": SPENT_RESERVE,
        "SPENT_RESERVE_STATUS": SPENT_RESERVE_STATUS,
        "STAGE_A_BEST": PREVIOUS_STAGE_A_BEST_SHA256,
        "STAGE_A_BEST_MUTATED": False,
        "TRAIN": False,
        "TRAINING_CONFIG_SHA256": AUTHORIZED_TRAINING_CONFIG_SHA256,
        "TRAINING_RESULT_RECEIPT_SHA256": TRAINING_RESULT_RECEIPT_SHA256,
        "V1R2_MUTATED": False,
        "authoritative_selected_head_source": source_audit.get(
            "authoritative_selected_head_source"
        ),
        "cold_load": dict(cold_load) if cold_load else None,
        "code_revision": code_revision,
        "forbidden_head_sources": list(FORBIDDEN_HEAD_SOURCES),
        "historical_incomplete_checkpoint": {
            "sha256": INCOMPLETE_SELECTED_CHECKPOINT_SHA256,
            "status": INCOMPLETE_CHECKPOINT_STATUS,
            "promotability": INCOMPLETE_CHECKPOINT_PROMOTABILITY,
            "deleted": False,
        },
        "identity_verification": dict(identity),
        "logit_parity": dict(logit_parity) if logit_parity else None,
        "reason": reason,
        "repaired_at": repaired_at or utc_now_iso(),
        "schema": SCHEMA_REPAIR,
        "serialization_regression_tests": dict(serialization_tests),
        "source_audit": dict(source_audit),
        "tensor_parity": dict(tensor_parity) if tensor_parity else None,
        "validation_replay": dict(validation_replay) if validation_replay else None,
    }
    payload["CHECKPOINT_REPAIR_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in payload.items()
                if k != "CHECKPOINT_REPAIR_RECEIPT_SHA256"
            }
        )
    )
    return payload
