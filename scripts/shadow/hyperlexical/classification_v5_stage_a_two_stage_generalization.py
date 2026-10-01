"""AUTHORIZE_V5_STAGE_A_TWO_STAGE_RETRAIN_ON_GENERALIZATION_SURFACE.

Fresh two-stage Stage-A retrain authorization bound to V1R1 generalization
surface. Does not overwrite HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-001,
mutate V1R1, train, touch spent reserve, or move BEST pointers.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .classification_v5_stage_a import (
    ACCEPTANCE_GATES,
    BEST_SHA,
    CLASS_WEIGHT_POLICY,
    LABEL_PROVENANCE_RULE,
    PROVENANCE_LOSS_MULTIPLIERS,
    TRAIN_HYPERPARAMS,
    canonical_json,
    sha256_text,
)
from .classification_v5_stage_a_generalization_surface import (
    PARENT_SURFACE_SHA_V1,
    SURFACE_RULE_V1R1,
)
from .classification_v5_stage_a_gold_label_mapping import RULE_ID as GOLD_LABEL_RULE
from .classification_v5_stage_a_two_stage import (
    ARCHITECTURE_RECEIPT_SHA256,
    CHECKPOINT_SELECTION,
    CLASS_WEIGHT_FORMULA_VERSION,
    DROP_LAST,
    FLAT_HEAD_STATUS,
    GATE1_LABELS,
    GATE1_THRESHOLDS,
    GATE2_LABELS,
    GATE2_PRESENT_THRESHOLDS,
    LAMBDA_GATE2,
    LAST_TRAINABLE_ENCODER_LAYERS,
    REPLACEMENT,
    SAMPLER,
    SCHEMA_AUTHORIZATION,
    SCHEMA_CLASS_WEIGHTS,
    SCHEMA_CONFIG,
    THRESHOLD_SELECTION,
    TWO_STAGE_RULE,
    architecture_contract,
    compute_gate1_class_weights,
    compute_gate2_class_weights,
    forward_contract_schema,
    gate2_eligible,
    gold_mapping_contract_sha256,
    identity_list_sha256,
    label_provenance_contract_sha256,
    loss_contract,
)

AUTHORIZE_RULE = "AUTHORIZE_V5_STAGE_A_TWO_STAGE_RETRAIN_ON_GENERALIZATION_SURFACE"
CLASS_WEIGHT_RESOLUTION_RULE = "RESOLVE_V5_STAGE_A_V1R1_TWO_STAGE_CLASS_WEIGHTS"
TRAIN_RULE = "HYPERLEX_V5_STAGE_A_TWO_STAGE_GENERALIZATION_TRAIN_V1"
TRAIN_ONCE_ACTION = "TRAIN_V5_STAGE_A_TWO_STAGE_GENERALIZATION_ONCE"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-GENERALIZATION-001"
PARENT_TWO_STAGE_EXPERIMENT_ID = "HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-001"

AUTHORIZED_DATASET_SHA = (
    "4095036e5af3ad7cfe9f038dd3e1f46e4ef0ea18db4c4b7186fc2b02e96d4274"
)
AUTHORIZED_READINESS_SHA = (
    "c4b5fc0725b919c1dd11acfd575d594d8ddd76839836e5a3928f4d6c07030c96"
)
AUTHORIZED_SURFACE_RECEIPT_SHA = (
    "3dbdd9b2cc30600698340f979d20a2c9b8559b9eafbbc24baf4fb1007e737fb9"
)
AUTHORIZED_REMEDIATION_DELTA_SHA = (
    "f560fb93302bd30980db8f5dd2ba8aaac1ecad1adf6a3a34e42e631bab70a006"
)
AUTHORIZED_SURFACE_RULE = SURFACE_RULE_V1R1
AUTHORIZED_SURFACE_VERSION = (
    "classification-v5-stage-a-generalization-surface-v1r1-20261001"
)
AUTHORIZED_BEST_SHA = BEST_SHA  # model-wide BEST
PARENT_STAGE_A_BEST_SHA = (
    "cd2829c1b5fb823fc03f18efe66a7387124ef44be2545b9e385a17eb6237bf5c"
)
PARENT_GENERALIZATION_SURFACE_SHA = PARENT_SURFACE_SHA_V1

EXPECTED_TRAIN_ROWS = 2531
EXPECTED_VALIDATION_ROWS = 1054
EXPECTED_TRAIN_SPLIT_SHA256 = (
    "d8565270bcc391e6e2c7967b679f88b598ce397d4e1031e8155a89c6beea2973"
)
EXPECTED_VALIDATION_SPLIT_SHA256 = (
    "3b8d588d7413099fb0e64ea89c162adacc8ec2b7d5beae910af48a828cb65869"
)
EXPECTED_TRAIN_IDENTITY_LIST_SHA256 = (
    "5a6f98c63d41b3cb145d454ed790f4c3e41049cf4cd6ffcea1c5e3d91e5de345"
)
EXPECTED_VALIDATION_IDENTITY_LIST_SHA256 = (
    "8264c9460c74a150d590dd4634e15db6c44319c879d2917891e9914a252c1c8d"
)

# Existing two-stage train contract: trunk + MODEL_WIDE_BEST encoder overlay;
# gate heads freshly Xavier-initialized. Explicitly NOT STAGE_A_BEST continuation.
INITIALIZATION_POLICY = {
    "base_encoder_sha256": AUTHORIZED_BEST_SHA,
    "base_encoder_source": "MODEL_WIDE_BEST",
    "conflict_with_stage_a_best_continuation": False,
    "gate_heads": "fresh_xavier_uniform_bias_zeros",
    "head_init": TRAIN_HYPERPARAMS["head_init"],
    "last_two_encoder_layers_source": "MODEL_WIDE_BEST_overlay",
    "policy": (
        "FRESH_RETRAIN_FROM_MODEL_WIDE_BEST:"
        "encoder_overlay_from_9fba0f66; "
        "gate1/gate2 heads freshly initialized; "
        "do_not_load_STAGE_A_BEST_cd2829c1"
    ),
    "scientific_interpretation": (
        "V1R1 is a fresh retraining comparison, not fine-tuning the previous "
        "Stage-A candidate on a remediation surface."
    ),
    "stage_a_best_continuation": False,
    "stage_a_best_sha256_reference_only": PARENT_STAGE_A_BEST_SHA,
    "trunk": "ModernBERT-base",
}

SPENT_RESERVE = "HYPERLEX_V5_PROMOTION_RESERVE_001"
SPENT_RESERVE_STATUS = "SPENT"
SPENT_RESERVE_OVERLAP = 0


def verify_v1r1_split_pins(
    *,
    train_rows: Sequence[Mapping[str, Any]],
    validation_rows: Sequence[Mapping[str, Any]],
    train_split_sha256: str,
    validation_split_sha256: str,
    train_identity_list_sha256: str,
    validation_identity_list_sha256: str,
) -> dict[str, Any]:
    train_ids = [str(r["identity"]) for r in train_rows]
    val_ids = [str(r["identity"]) for r in validation_rows]
    checks = {
        "train_count": len(train_rows) == EXPECTED_TRAIN_ROWS,
        "validation_count": len(validation_rows) == EXPECTED_VALIDATION_ROWS,
        "train_split_sha256": train_split_sha256 == EXPECTED_TRAIN_SPLIT_SHA256,
        "validation_split_sha256": (
            validation_split_sha256 == EXPECTED_VALIDATION_SPLIT_SHA256
        ),
        "train_identity_list_sha256": (
            train_identity_list_sha256 == EXPECTED_TRAIN_IDENTITY_LIST_SHA256
            and identity_list_sha256(train_ids) == EXPECTED_TRAIN_IDENTITY_LIST_SHA256
        ),
        "validation_identity_list_sha256": (
            validation_identity_list_sha256 == EXPECTED_VALIDATION_IDENTITY_LIST_SHA256
            and identity_list_sha256(val_ids) == EXPECTED_VALIDATION_IDENTITY_LIST_SHA256
        ),
        "train_val_identity_overlap": len(set(train_ids) & set(val_ids)) == 0,
    }
    checks["pass"] = all(checks.values())
    return {
        "checks": checks,
        "expected": {
            "TRAIN_IDENTITY_LIST_SHA256": EXPECTED_TRAIN_IDENTITY_LIST_SHA256,
            "TRAIN_ROWS": EXPECTED_TRAIN_ROWS,
            "TRAIN_SPLIT_SHA256": EXPECTED_TRAIN_SPLIT_SHA256,
            "VALIDATION_IDENTITY_LIST_SHA256": EXPECTED_VALIDATION_IDENTITY_LIST_SHA256,
            "VALIDATION_ROWS": EXPECTED_VALIDATION_ROWS,
            "VALIDATION_SPLIT_SHA256": EXPECTED_VALIDATION_SPLIT_SHA256,
        },
        "pass": checks["pass"],
    }


def resolve_v1r1_two_stage_class_weights(
    train_rows: Sequence[Mapping[str, Any]],
    *,
    dataset_sha256: str,
    train_split_sha256: str,
    train_identity_list_sha256: str,
    code_revision: str,
) -> dict[str, Any]:
    """RESOLVE_V5_STAGE_A_V1R1_TWO_STAGE_CLASS_WEIGHTS — train split only."""
    if not train_rows:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:empty_train")
    if dataset_sha256 != AUTHORIZED_DATASET_SHA:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:dataset_mismatch")
    if train_split_sha256 != EXPECTED_TRAIN_SPLIT_SHA256:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:train_split_mismatch")
    if train_identity_list_sha256 != EXPECTED_TRAIN_IDENTITY_LIST_SHA256:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:train_identity_mismatch")
    if len(train_rows) != EXPECTED_TRAIN_ROWS:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:train_count_mismatch")

    n_train = len(train_rows)
    n_none = sum(1 for r in train_rows if str(r["evidence_label"]) == "NO_EVIDENCE")
    n_present = sum(
        1 for r in train_rows if str(r["evidence_label"]) == "EVIDENCE_PRESENT"
    )
    n_uncertain = sum(1 for r in train_rows if str(r["evidence_label"]) == "UNCERTAIN")
    if n_none + n_present + n_uncertain != n_train:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:unexpected_gold_labels")

    gate1 = compute_gate1_class_weights(train_rows)
    gate2 = compute_gate2_class_weights(train_rows)

    g1_rows = sum(gate1["accounts"][label]["rows"] for label in GATE1_LABELS)
    if g1_rows != n_train:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:gate1_row_cover")
    if gate1["accounts"]["NO_EVIDENCE"]["rows"] != n_none:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:gate1_none_count")
    if gate1["accounts"]["POSSIBLE_EVIDENCE"]["rows"] != n_present + n_uncertain:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:gate1_possible_count")
    if gate2["n_eligible_train"] != n_present + n_uncertain:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:gate2_eligible_count")
    if gate2["accounts"]["UNCERTAIN"]["rows"] != n_uncertain:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:gate2_uncertain_count")
    if gate2["accounts"]["CONFIRMED_PRESENT"]["rows"] != n_present:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:gate2_present_count")

    gate1_possible_ids = sorted(
        str(r["identity"])
        for r in train_rows
        if str(r["evidence_label"]) in {"EVIDENCE_PRESENT", "UNCERTAIN"}
    )
    gate2_eligible_ids = sorted(
        str(r["identity"])
        for r in train_rows
        if gate2_eligible(str(r["evidence_label"]))
    )
    gate1_possible_id_sha = identity_list_sha256(gate1_possible_ids)
    gate2_eligible_id_sha = identity_list_sha256(gate2_eligible_ids)
    if gate1_possible_ids != gate2_eligible_ids:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:gate2_identity_set_mismatch")
    if gate1_possible_id_sha != gate2_eligible_id_sha:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:gate2_identity_hash_mismatch")

    literal_weights = {
        "gate1": {
            "NO_EVIDENCE": float(gate1["class_weights"]["NO_EVIDENCE"]),
            "POSSIBLE_EVIDENCE": float(gate1["class_weights"]["POSSIBLE_EVIDENCE"]),
        },
        "gate2": {
            "UNCERTAIN": float(gate2["class_weights"]["UNCERTAIN"]),
            "CONFIRMED_PRESENT": float(gate2["class_weights"]["CONFIRMED_PRESENT"]),
        },
    }
    payload = {
        "CLASS_WEIGHT_RESOLUTION_RULE": CLASS_WEIGHT_RESOLUTION_RULE,
        "Gate1": {
            "NO_EVIDENCE": dict(gate1["accounts"]["NO_EVIDENCE"]),
            "POSSIBLE_EVIDENCE": dict(gate1["accounts"]["POSSIBLE_EVIDENCE"]),
            "class_weights": dict(literal_weights["gate1"]),
            "coverage": {
                "n_none": n_none,
                "n_possible": n_present + n_uncertain,
                "n_train": n_train,
            },
            "possible_evidence_identity_list_sha256": gate1_possible_id_sha,
        },
        "Gate2": {
            "UNCERTAIN": dict(gate2["accounts"]["UNCERTAIN"]),
            "CONFIRMED_PRESENT": dict(gate2["accounts"]["CONFIRMED_PRESENT"]),
            "class_weights": dict(literal_weights["gate2"]),
            "coverage": {
                "n_eligible": n_present + n_uncertain,
                "n_none_excluded": n_none,
                "n_present": n_present,
                "n_uncertain": n_uncertain,
            },
            "eligible_identity_list_sha256": gate2_eligible_id_sha,
        },
        "clip_policy": {
            "max": CLASS_WEIGHT_POLICY["clip_max"],
            "min": CLASS_WEIGHT_POLICY["clip_min"],
            "renormalize_after_clip": False,
        },
        "code_revision": code_revision,
        "dataset_sha256": dataset_sha256,
        "literal_weights": literal_weights,
        "provenance_weights": dict(PROVENANCE_LOSS_MULTIPLIERS),
        "resolution_formula_version": CLASS_WEIGHT_FORMULA_VERSION,
        "schema": SCHEMA_CLASS_WEIGHTS,
        "surface_rule": AUTHORIZED_SURFACE_RULE,
        "surface_version": AUTHORIZED_SURFACE_VERSION,
        "train_identity_list_sha256": train_identity_list_sha256,
        "train_only": True,
        "train_split_sha256": train_split_sha256,
    }
    payload["CLASS_WEIGHT_ARTIFACT_SHA256"] = sha256_text(
        canonical_json(
            {k: v for k, v in payload.items() if k != "CLASS_WEIGHT_ARTIFACT_SHA256"}
        )
    )
    return payload


def generalization_resolved_config(
    *,
    dataset_sha256: str,
    class_weight_artifact: Mapping[str, Any],
    code_revision: str,
    tokenizer_identity: str,
    train_split_sha256: str,
    validation_split_sha256: str,
    train_identity_list_sha256: str,
    validation_identity_list_sha256: str,
    readiness_sha256: str,
    surface_receipt_sha256: str,
) -> dict[str, Any]:
    if dataset_sha256 != AUTHORIZED_DATASET_SHA:
        raise ValueError("dataset_sha_mismatch")
    if readiness_sha256 != AUTHORIZED_READINESS_SHA:
        raise ValueError("readiness_sha_mismatch")
    if surface_receipt_sha256 != AUTHORIZED_SURFACE_RECEIPT_SHA:
        raise ValueError("surface_receipt_sha_mismatch")
    if train_split_sha256 != EXPECTED_TRAIN_SPLIT_SHA256:
        raise ValueError("train_split_sha_mismatch")
    if validation_split_sha256 != EXPECTED_VALIDATION_SPLIT_SHA256:
        raise ValueError("validation_split_sha_mismatch")
    if train_identity_list_sha256 != EXPECTED_TRAIN_IDENTITY_LIST_SHA256:
        raise ValueError("train_identity_sha_mismatch")
    if validation_identity_list_sha256 != EXPECTED_VALIDATION_IDENTITY_LIST_SHA256:
        raise ValueError("validation_identity_sha_mismatch")

    literal = class_weight_artifact["literal_weights"]
    config = {
        "acceptance_gates": dict(ACCEPTANCE_GATES),
        "architecture": architecture_contract(),
        "architecture_receipt_sha256": ARCHITECTURE_RECEIPT_SHA256,
        "architecture_rule": TWO_STAGE_RULE,
        "best_encoder_sha256": AUTHORIZED_BEST_SHA,
        "checkpoint_selection": dict(CHECKPOINT_SELECTION),
        "class_weight_artifact_sha256": class_weight_artifact[
            "CLASS_WEIGHT_ARTIFACT_SHA256"
        ],
        "code_revision": code_revision,
        "dataset_sha256": dataset_sha256,
        "diagnostic_cells": [
            "SHORT_ATOM/NO_EVIDENCE",
            "SHORT_ATOM/EVIDENCE_PRESENT",
            "DEFINITION_STYLE/NO_EVIDENCE",
            "DEFINITION_STYLE/EVIDENCE_PRESENT",
            "PROSE/NO_EVIDENCE",
            "PROSE/EVIDENCE_PRESENT",
            "ORDINARY_PROSE/NO_EVIDENCE",
            "ORDINARY_PROSE/EVIDENCE_PRESENT",
        ],
        "diagnostic_slices": [
            "provenance",
            "source_family",
            "domain",
            "length_band",
            "label_authority",
        ],
        "experiment_id": EXPERIMENT_ID,
        "flat_head_status": FLAT_HEAD_STATUS,
        "forward": forward_contract_schema(),
        "gate1_class_weights_literal": dict(literal["gate1"]),
        "gate1_gold_mapping": {
            "EVIDENCE_PRESENT": 1,
            "NO_EVIDENCE": 0,
            "UNCERTAIN": 1,
        },
        "gate2_class_weights_literal": dict(literal["gate2"]),
        "gate2_gold_mapping": {
            "EVIDENCE_PRESENT": 1,
            "UNCERTAIN": 0,
        },
        "gate2_mask_rule": "gold_NO_EVIDENCE_excluded_from_gate2_loss",
        "gold_label_rule": GOLD_LABEL_RULE,
        "gold_mapping_sha256": gold_mapping_contract_sha256(),
        "initialization_policy": dict(INITIALIZATION_POLICY),
        "label_provenance_contract_sha256": label_provenance_contract_sha256(),
        "label_provenance_rule": LABEL_PROVENANCE_RULE,
        "loss": loss_contract(),
        "model_wide_best_sha256": AUTHORIZED_BEST_SHA,
        "optimization": {
            "early_stopping_patience": TRAIN_HYPERPARAMS["early_stopping_patience"],
            "gradient_accumulation": TRAIN_HYPERPARAMS["gradient_accumulation"],
            "learning_rate": TRAIN_HYPERPARAMS["learning_rate"],
            "max_epochs": TRAIN_HYPERPARAMS["max_epochs"],
            "max_grad_norm": TRAIN_HYPERPARAMS["max_grad_norm"],
            "micro_batch_size": TRAIN_HYPERPARAMS["micro_batch_size"],
            "minimum_epochs": TRAIN_HYPERPARAMS["minimum_epochs"],
            "mixed_precision": TRAIN_HYPERPARAMS["mixed_precision"],
            "optimizer": TRAIN_HYPERPARAMS["optimizer"],
            "warmup_ratio": TRAIN_HYPERPARAMS["warmup_ratio"],
            "weight_decay": TRAIN_HYPERPARAMS["weight_decay"],
        },
        "parent_generalization_surface_sha256": PARENT_GENERALIZATION_SURFACE_SHA,
        "parent_stage_a_best_sha256": PARENT_STAGE_A_BEST_SHA,
        "parent_two_stage_experiment_id": PARENT_TWO_STAGE_EXPERIMENT_ID,
        "provenance_weights": dict(PROVENANCE_LOSS_MULTIPLIERS),
        "readiness_sha256": readiness_sha256,
        "rule": TWO_STAGE_RULE,
        "sampler": {
            "class_balanced_sampler": False,
            "drop_last": DROP_LAST,
            "oversampling": False,
            "replacement": REPLACEMENT,
            "sampler": SAMPLER,
            "undersampling": False,
        },
        "schema": SCHEMA_CONFIG,
        "seed": TRAIN_HYPERPARAMS["seed"],
        "spent_reserve": SPENT_RESERVE,
        "spent_reserve_access": "FORBIDDEN_FOR_TRAIN_VAL_THRESHOLD_CHECKPOINT",
        "spent_reserve_overlap": SPENT_RESERVE_OVERLAP,
        "spent_reserve_status": SPENT_RESERVE_STATUS,
        "split": {
            "TRAIN_IDENTITY_LIST_SHA256": train_identity_list_sha256,
            "TRAIN_ROWS": EXPECTED_TRAIN_ROWS,
            "TRAIN_SPLIT_SHA256": train_split_sha256,
            "VALIDATION_IDENTITY_LIST_SHA256": validation_identity_list_sha256,
            "VALIDATION_ROWS": EXPECTED_VALIDATION_ROWS,
            "VALIDATION_SPLIT_SHA256": validation_split_sha256,
            "regenerate_split": False,
        },
        "surface_receipt_sha256": surface_receipt_sha256,
        "surface_rule": AUTHORIZED_SURFACE_RULE,
        "surface_version": AUTHORIZED_SURFACE_VERSION,
        "threshold_grids": {
            "gate1_thresholds": list(GATE1_THRESHOLDS),
            "gate2_present_thresholds": list(GATE2_PRESENT_THRESHOLDS),
            "n_combinations": 100,
        },
        "threshold_selection": dict(THRESHOLD_SELECTION),
        "tokenization": {
            "max_length": TRAIN_HYPERPARAMS["max_len"],
            "padding": TRAIN_HYPERPARAMS["padding"],
            "tokenizer_identity": tokenizer_identity,
            "truncation": TRAIN_HYPERPARAMS["truncation"],
        },
        "train_rule": TRAIN_RULE,
        "train_run_limit": 1,
        "trainable": {
            "gate1_head": True,
            "gate2_head": True,
            "last_trainable_encoder_layers": LAST_TRAINABLE_ENCODER_LAYERS,
            "mutate_best": False,
        },
    }
    config["training_config_sha256"] = sha256_text(
        canonical_json({k: v for k, v in config.items() if k != "training_config_sha256"})
    )
    return config


def generalization_authorization_contract(
    *,
    dataset_sha256: str,
    training_config_sha256: str,
    class_weight_artifact_sha256: str,
    code_revision: str,
    readiness_sha256: str,
    surface_receipt_sha256: str,
) -> dict[str, Any]:
    if dataset_sha256 != AUTHORIZED_DATASET_SHA:
        raise ValueError("dataset_sha_mismatch")
    if readiness_sha256 != AUTHORIZED_READINESS_SHA:
        raise ValueError("readiness_sha_mismatch")
    if surface_receipt_sha256 != AUTHORIZED_SURFACE_RECEIPT_SHA:
        raise ValueError("surface_receipt_sha_mismatch")
    return {
        "AUTHORIZE_RULE": AUTHORIZE_RULE,
        "ARCHITECTURE_RECEIPT_SHA256": ARCHITECTURE_RECEIPT_SHA256,
        "BEST": "UNCHANGED",
        "BEST_MUTATED": False,
        "CLASS_WEIGHT_ARTIFACT_SHA256": class_weight_artifact_sha256,
        "CURRENT_BEST": AUTHORIZED_BEST_SHA,
        "DATASET_SHA256": dataset_sha256,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "MODEL_WIDE_BEST": AUTHORIZED_BEST_SHA,
        "MODEL_WIDE_BEST_MUTATED": False,
        "PARENT_STAGE_A_BEST": PARENT_STAGE_A_BEST_SHA,
        "PARENT_STAGE_A_BEST_MUTATED": False,
        "READINESS_SHA256": readiness_sha256,
        "RESERVE_CONSUMED": False,
        "SCIENTIFIC_RESULT": "NOT_COMPUTABLE",
        "STAGE_B_MUTATED": False,
        "SURFACE_RECEIPT_SHA256": surface_receipt_sha256,
        "TRAINING_CONFIG_SHA256": training_config_sha256,
        "TRAINING_RUN_LIMIT": 1,
        "TRAINING_STATUS": "AUTHORIZED_NOT_STARTED",
        "TRAIN_AUTHORIZED": True,
        "authorized_best_sha256": AUTHORIZED_BEST_SHA,
        "authorized_dataset_sha256": AUTHORIZED_DATASET_SHA,
        "code_revision": code_revision,
        "flat_head_status": FLAT_HEAD_STATUS,
        "initialization_policy": dict(INITIALIZATION_POLICY),
        "parent_two_stage_experiment_id": PARENT_TWO_STAGE_EXPERIMENT_ID,
        "prior_run_count": 0,
        "rule": TRAIN_RULE,
        "schema": SCHEMA_AUTHORIZATION,
        "spent_reserve": SPENT_RESERVE,
        "spent_reserve_overlap": SPENT_RESERVE_OVERLAP,
        "spent_reserve_status": SPENT_RESERVE_STATUS,
        "surface_rule": AUTHORIZED_SURFACE_RULE,
        "surface_version": AUTHORIZED_SURFACE_VERSION,
        "train": False,
        "train_authorized": True,
        "two_stage_architecture_rule": TWO_STAGE_RULE,
    }


def generalization_runner_authorization_checks(
    *,
    train_authorized: bool,
    experiment_id: str,
    dataset_sha256: str,
    architecture_receipt_sha256: str,
    resolved_config_sha256: str,
    authorized_config_sha256: str,
    best_sha256: str,
    stage_a_best_sha256: str,
    surface_readiness: str,
    label_mapping: str,
    label_provenance_invalid_rows: int,
    prior_run_count: int,
    reserve_consumed: bool,
    class_weight_artifact_sha256: str,
    authorized_class_weight_artifact_sha256: str,
    readiness_sha256: str,
    surface_receipt_sha256: str,
    initialization_stage_a_best_continuation: bool,
) -> dict[str, Any]:
    checks = {
        "architecture_receipt": architecture_receipt_sha256
        == ARCHITECTURE_RECEIPT_SHA256,
        "best": best_sha256 == AUTHORIZED_BEST_SHA,
        "class_weight_artifact": class_weight_artifact_sha256
        == authorized_class_weight_artifact_sha256,
        "dataset_sha256": dataset_sha256 == AUTHORIZED_DATASET_SHA,
        "experiment_id": experiment_id == EXPERIMENT_ID,
        "initialization_not_stage_a_best_continuation": (
            initialization_stage_a_best_continuation is False
        ),
        "label_mapping": label_mapping == "PASS",
        "label_provenance_invalid_rows": label_provenance_invalid_rows == 0,
        "parent_stage_a_best_reference": stage_a_best_sha256 == PARENT_STAGE_A_BEST_SHA,
        "prior_run_count": prior_run_count == 0,
        "readiness_sha256": readiness_sha256 == AUTHORIZED_READINESS_SHA,
        "reserve_consumed": reserve_consumed is False,
        "resolved_config_sha256": resolved_config_sha256 == authorized_config_sha256,
        "surface_readiness": surface_readiness == "PASS",
        "surface_receipt_sha256": surface_receipt_sha256
        == AUTHORIZED_SURFACE_RECEIPT_SHA,
        "train_authorized": train_authorized is True,
    }
    checks["pass"] = all(checks.values())
    return checks
