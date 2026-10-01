"""AUTHORIZE_STAGE_A_FACTORIZED_RELATION_TRAIN — auth + class-weight resolution.

Resolves fresh train-only relation/resolvability class weights from sealed
V1R1 + factorized annotations. Does not train, mutate V1R1/annotations,
alter Stage B, access spent reserve, or move BEST.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .classification_v5_stage_a import (
    ACCEPTANCE_GATES,
    BEST_SHA,
    CLASS_WEIGHT_POLICY,
    PROVENANCE_LOSS_MULTIPLIERS,
    TRAIN_HYPERPARAMS,
    canonical_json,
    sha256_text,
)
from .classification_v5_stage_a_factorized_objective import (
    DOMAIN_IRRELEVANT_GENERALIZATION,
    EXPERIMENT_ID,
    FACTORIZED_ANNOTATION_SHA256_PIN,
    FACTORIZED_OBJECTIVE_SPEC,
    LAMBDA_RESOLVABILITY,
    MASKED,
    OBJECTIVE_ID,
    OBJECTIVE_RECEIPT_SHA256_PIN,
    OBJECTIVE_RULE,
    PARENT_DECOMPOSITION,
    POSSIBLE_EVIDENCE_STATUS,
    RELATION_LABELS,
    RELATION_THRESHOLDS,
    RESOLVABILITY_LABELS,
    RESOLVABILITY_THRESHOLDS,
    SEMANTIC_DECOMPOSITION_RECEIPT_SHA256,
    architecture_contract,
    decide_stage_a,
    loss_contract,
    relation_loss_eligible,
)
from .classification_v5_stage_a_two_stage import (
    DROP_LAST,
    _empty_class_account,
    _finalize_binary_accounts,
    _account_row,
    identity_list_sha256,
    provenance_multiplier,
)
from .classification_v5_stage_a_two_stage_generalization import (
    AUTHORIZED_DATASET_SHA,
    AUTHORIZED_READINESS_SHA,
    AUTHORIZED_SURFACE_RECEIPT_SHA,
    AUTHORIZED_SURFACE_RULE,
    AUTHORIZED_SURFACE_VERSION,
    EXPECTED_OPTIMIZER_STEPS_PER_EPOCH,
    EXPECTED_TRAIN_IDENTITY_LIST_SHA256,
    EXPECTED_TRAIN_ROWS,
    EXPECTED_TRAIN_SPLIT_SHA256,
    EXPECTED_VALIDATION_IDENTITY_LIST_SHA256,
    EXPECTED_VALIDATION_ROWS,
    EXPECTED_VALIDATION_SPLIT_SHA256,
    PARENT_STAGE_A_BEST_SHA,
    SPENT_RESERVE,
    SPENT_RESERVE_OVERLAP,
    SPENT_RESERVE_STATUS,
    verify_v1r1_split_pins,
)

AUTHORIZE_RULE = "AUTHORIZE_STAGE_A_FACTORIZED_RELATION_TRAIN"
CLASS_WEIGHT_RESOLUTION_RULE = "RESOLVE_STAGE_A_FACTORIZED_RELATION_CLASS_WEIGHTS"
CLASS_WEIGHT_FORMULA_VERSION = "HYPERLEX_V5_FACTORIZED_RELATION_CLASS_WEIGHTS_V1"
TRAIN_ONCE_ACTION = "TRAIN_STAGE_A_FACTORIZED_RELATION_ONCE"
TRAIN_RULE = "HYPERLEX_V5_STAGE_A_FACTORIZED_RELATION_TRAIN_V1"

SCHEMA_CLASS_WEIGHTS = (
    "hyperlex.classification.v5.stage_a_factorized_relation_class_weights.v1"
)
SCHEMA_AUTH = "hyperlex.classification.v5.stage_a_factorized_relation_authorization.v1"
SCHEMA_CONFIG = (
    "hyperlex.classification.v5.stage_a_factorized_relation_training_config.v1"
)

# Sealed by AUTHORIZE_STAGE_A_FACTORIZED_RELATION_TRAIN (2026-10-01).
AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256 = (
    "47e5877338e363ac2dbf6b32d0f7ab8048370d9727ecfe7ec2f32118ffcc5ad6"
)
AUTHORIZED_TRAINING_CONFIG_SHA256 = (
    "618079c7d797ddae98c3b0961f1fe7a6954f32983560971fa4c50821facae751"
)
AUTHORIZED_AUTH_RECEIPT_SHA256 = (
    "133d8dd0bd347e2f5b905a20cbb4acf216f524110c8d553c7a6fdb89c1020f5a"
)

LITERAL_RELATION_WEIGHTS: dict[str, float] = {
    "NO_EVIDENCE_RELATION": 0.9538023229441501,
    "EVIDENCE_RELATION_PRESENT": 1.0461976770558497,
}
LITERAL_RESOLVABILITY_WEIGHTS: dict[str, float] = {
    "UNRESOLVABLE": 1.5314299338122987,
    "RESOLVABLE": 0.5,
}

INITIALIZATION_POLICY = {
    "base_encoder_sha256": BEST_SHA,
    "base_encoder_source": "MODEL_WIDE_BEST",
    "conflict_with_stage_a_best_continuation": False,
    "head_init": TRAIN_HYPERPARAMS["head_init"],
    "last_two_encoder_layers_source": "MODEL_WIDE_BEST_overlay",
    "policy": (
        "FRESH_RETRAIN_FROM_MODEL_WIDE_BEST:"
        "encoder_overlay_from_9fba0f66; "
        "relation_head/resolvability_head freshly Xavier-initialized; "
        "do_not_load_STAGE_A_BEST_cd2829c1"
    ),
    "relation_head": "fresh_xavier_uniform_bias_zeros",
    "resolvability_head": "fresh_xavier_uniform_bias_zeros",
    "scientific_interpretation": (
        "Factorized relation objective fresh retrain from MODEL_WIDE_BEST; "
        "not a STAGE_A_BEST continuation."
    ),
    "stage_a_best_continuation": False,
    "stage_a_best_sha256_reference_only": PARENT_STAGE_A_BEST_SHA,
    "trunk": "ModernBERT-base",
}

CHECKPOINT_SELECTION = {
    "formula": "0.50 * relation_macro_F1 + 0.50 * resolvability_macro_F1",
    "relation_scope": "relation_loss_eligible_validation_rows",
    "resolvability_scope": "all_validation_rows",
    "strict_improvement": True,
    "tie_break": [
        "lower_relation_false_positive_rate",
        "higher_relation_positive_recall",
        "higher_resolvability_UNRESOLVABLE_recall",
        "earlier_epoch",
    ],
}

THRESHOLD_SELECTION = {
    "acceptance_required": [
        "false_evidence_entry_rate_on_none <= 0.05",
        "EVIDENCE_PRESENT_recall >= 0.70",
        "NO_EVIDENCE_recall >= 0.90",
    ],
    "maximize_in_order": [
        "stage_a_macro_f1",
        "EVIDENCE_PRESENT_recall",
        "UNCERTAIN_recall",
        "minimize_false_evidence_entry",
        "higher_relation_threshold",
        "higher_resolvability_threshold",
    ],
    "fail_if_no_feasible": "SETTLED_FAIL",
    "n_grid_combinations": 100,
}


def load_annotation_index(
    annotations: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    index: dict[str, Mapping[str, Any]] = {}
    for ann in annotations:
        identity = str(ann["identity"])
        if identity in index:
            raise ValueError(f"DUPLICATE_ANNOTATION_IDENTITY:{identity}")
        index[identity] = ann
    return index


def resolve_factorized_relation_class_weights(
    train_rows: Sequence[Mapping[str, Any]],
    annotations: Sequence[Mapping[str, Any]],
    *,
    dataset_sha256: str,
    annotation_sha256: str,
    train_split_sha256: str,
    train_identity_list_sha256: str,
    code_revision: str,
) -> dict[str, Any]:
    """RESOLVE_STAGE_A_FACTORIZED_RELATION_CLASS_WEIGHTS — train split only."""
    if not train_rows:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:empty_train")
    if dataset_sha256 != AUTHORIZED_DATASET_SHA:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:dataset_mismatch")
    if annotation_sha256 != FACTORIZED_ANNOTATION_SHA256_PIN:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:annotation_mismatch")
    if train_split_sha256 != EXPECTED_TRAIN_SPLIT_SHA256:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:train_split_mismatch")
    if train_identity_list_sha256 != EXPECTED_TRAIN_IDENTITY_LIST_SHA256:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:train_identity_mismatch")
    if len(train_rows) != EXPECTED_TRAIN_ROWS:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:train_count_mismatch")

    ann_index = load_annotation_index(annotations)
    relation_accounts = {label: _empty_class_account() for label in RELATION_LABELS}
    resolvability_accounts = {
        label: _empty_class_account() for label in RESOLVABILITY_LABELS
    }

    relation_eligible_ids: list[str] = []
    relation_masked_ids: list[str] = []
    ambiguous_ids: list[str] = []

    for row in train_rows:
        identity = str(row["identity"])
        ann = ann_index.get(identity)
        if ann is None:
            raise ValueError(f"CLASS_WEIGHT_RESOLUTION_INVALID:missing_annotation:{identity}")
        if str(ann["source_gold_label"]) != str(row["evidence_label"]):
            raise ValueError(
                f"CLASS_WEIGHT_RESOLUTION_INVALID:gold_mismatch:{identity}"
            )
        if str(ann["source_subtype"]) != str(row.get("evidence_subtype") or ""):
            raise ValueError(
                f"CLASS_WEIGHT_RESOLUTION_INVALID:subtype_mismatch:{identity}"
            )

        if str(row.get("evidence_subtype") or "") == "AMBIGUOUS_EVIDENCE":
            ambiguous_ids.append(identity)

        # Resolvability: all rows.
        resolvable = int(ann["semantic_resolvable"])
        res_label = RESOLVABILITY_LABELS[resolvable]
        _account_row(resolvability_accounts[res_label], row.get("provenance"))

        # Relation: exclude MASKED.
        rel = ann["evidence_relation_present"]
        if rel == MASKED:
            relation_masked_ids.append(identity)
            if int(ann["semantic_resolvable"]) != 0:
                raise ValueError(
                    f"CLASS_WEIGHT_RESOLUTION_INVALID:masked_but_resolvable:{identity}"
                )
            continue
        if rel not in (0, 1):
            raise ValueError(
                f"CLASS_WEIGHT_RESOLUTION_INVALID:bad_relation_target:{identity}:{rel}"
            )
        relation_eligible_ids.append(identity)
        rel_label = RELATION_LABELS[int(rel)]
        _account_row(relation_accounts[rel_label], row.get("provenance"))

    n_ambiguous = len(ambiguous_ids)
    if len(relation_eligible_ids) != EXPECTED_TRAIN_ROWS - n_ambiguous:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:relation_eligible_count")
    if len(relation_masked_ids) != n_ambiguous:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:masked_count")

    masked_sha = identity_list_sha256(relation_masked_ids)
    ambiguous_sha = identity_list_sha256(ambiguous_ids)
    if masked_sha != ambiguous_sha:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:masked_vs_ambiguous_hash")
    if sorted(relation_masked_ids) != sorted(ambiguous_ids):
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:masked_vs_ambiguous_set")

    relation_final = _finalize_binary_accounts(
        relation_accounts, labels=RELATION_LABELS
    )
    resolvability_final = _finalize_binary_accounts(
        resolvability_accounts, labels=RESOLVABILITY_LABELS
    )

    # Resolvability must cover all train rows.
    res_rows = sum(
        resolvability_final["accounts"][label]["rows"]
        for label in RESOLVABILITY_LABELS
    )
    if res_rows != EXPECTED_TRAIN_ROWS:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:resolvability_row_cover")

    literal_weights = {
        "relation": {
            label: float(relation_final["class_weights"][label])
            for label in RELATION_LABELS
        },
        "resolvability": {
            label: float(resolvability_final["class_weights"][label])
            for label in RESOLVABILITY_LABELS
        },
    }

    payload = {
        "CLASS_WEIGHT_RESOLUTION_RULE": CLASS_WEIGHT_RESOLUTION_RULE,
        "OBJECTIVE_ID": OBJECTIVE_ID,
        "annotation_sha256": annotation_sha256,
        "clip_policy": {
            "max": CLASS_WEIGHT_POLICY["clip_max"],
            "min": CLASS_WEIGHT_POLICY["clip_min"],
            "renormalize_after_clip": False,
        },
        "code_revision": code_revision,
        "dataset_sha256": dataset_sha256,
        "literal_weights": literal_weights,
        "provenance_weights": dict(PROVENANCE_LOSS_MULTIPLIERS),
        "relation": {
            "NO_EVIDENCE_RELATION": dict(
                relation_final["accounts"]["NO_EVIDENCE_RELATION"]
            ),
            "EVIDENCE_RELATION_PRESENT": dict(
                relation_final["accounts"]["EVIDENCE_RELATION_PRESENT"]
            ),
            "class_weights": dict(literal_weights["relation"]),
            "coverage": {
                "n_eligible": len(relation_eligible_ids),
                "n_masked": len(relation_masked_ids),
                "n_train": EXPECTED_TRAIN_ROWS,
                "n_ambiguous": n_ambiguous,
            },
            "eligible_identity_list_sha256": identity_list_sha256(
                relation_eligible_ids
            ),
            "masked_identity_list_sha256": masked_sha,
            "ambiguous_identity_list_sha256": ambiguous_sha,
        },
        "resolvability": {
            "UNRESOLVABLE": dict(resolvability_final["accounts"]["UNRESOLVABLE"]),
            "RESOLVABLE": dict(resolvability_final["accounts"]["RESOLVABLE"]),
            "class_weights": dict(literal_weights["resolvability"]),
            "coverage": {
                "n_eligible": EXPECTED_TRAIN_ROWS,
                "n_unresolvable": resolvability_final["accounts"]["UNRESOLVABLE"][
                    "rows"
                ],
                "n_resolvable": resolvability_final["accounts"]["RESOLVABLE"]["rows"],
            },
        },
        "resolution_formula_version": CLASS_WEIGHT_FORMULA_VERSION,
        "reused_gate1_gate2_weights": False,
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


def factorized_resolved_config(
    *,
    dataset_sha256: str,
    annotation_sha256: str,
    class_weight_artifact: Mapping[str, Any],
    code_revision: str,
    tokenizer_identity: str,
    train_split_sha256: str,
    validation_split_sha256: str,
    train_identity_list_sha256: str,
    validation_identity_list_sha256: str,
    readiness_sha256: str,
    surface_receipt_sha256: str,
    objective_receipt_sha256: str,
) -> dict[str, Any]:
    if dataset_sha256 != AUTHORIZED_DATASET_SHA:
        raise ValueError("resolved_config:dataset_mismatch")
    if annotation_sha256 != FACTORIZED_ANNOTATION_SHA256_PIN:
        raise ValueError("resolved_config:annotation_mismatch")
    if readiness_sha256 != AUTHORIZED_READINESS_SHA:
        raise ValueError("resolved_config:readiness_mismatch")
    if surface_receipt_sha256 != AUTHORIZED_SURFACE_RECEIPT_SHA:
        raise ValueError("resolved_config:surface_receipt_mismatch")
    if objective_receipt_sha256 != OBJECTIVE_RECEIPT_SHA256_PIN:
        raise ValueError("resolved_config:objective_receipt_mismatch")

    config = {
        "OBJECTIVE_ID": OBJECTIVE_ID,
        "OBJECTIVE_RULE": OBJECTIVE_RULE,
        "OBJECTIVE_RECEIPT_SHA256": objective_receipt_sha256,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "FACTORIZED_OBJECTIVE_SPEC": FACTORIZED_OBJECTIVE_SPEC,
        "PARENT_DECOMPOSITION": PARENT_DECOMPOSITION,
        "POSSIBLE_EVIDENCE_STATUS": POSSIBLE_EVIDENCE_STATUS,
        "DOMAIN_IRRELEVANT_GENERALIZATION": DOMAIN_IRRELEVANT_GENERALIZATION,
        "SEMANTIC_DECOMPOSITION_RECEIPT_SHA256": SEMANTIC_DECOMPOSITION_RECEIPT_SHA256,
        "acceptance_gates": dict(ACCEPTANCE_GATES),
        "annotation_sha256": annotation_sha256,
        "architecture": architecture_contract(),
        "checkpoint_selection": CHECKPOINT_SELECTION,
        "class_weight_artifact_sha256": class_weight_artifact[
            "CLASS_WEIGHT_ARTIFACT_SHA256"
        ],
        "code_revision": code_revision,
        "dataset_sha256": dataset_sha256,
        "drop_last": DROP_LAST,
        "early_stopping_patience": TRAIN_HYPERPARAMS["early_stopping_patience"],
        "expected_optimizer_steps_per_epoch": EXPECTED_OPTIMIZER_STEPS_PER_EPOCH,
        "expected_train_rows": EXPECTED_TRAIN_ROWS,
        "expected_validation_rows": EXPECTED_VALIDATION_ROWS,
        "gradient_accumulation": TRAIN_HYPERPARAMS["gradient_accumulation"],
        "head_definitions": {
            "relation_head": {
                "labels": list(RELATION_LABELS),
                "logits": 2,
                "mask": "evidence_relation_present == MASKED",
            },
            "resolvability_head": {
                "labels": list(RESOLVABILITY_LABELS),
                "logits": 2,
                "mask": None,
            },
            "domain_head": False,
        },
        "initialization_policy": INITIALIZATION_POLICY,
        "lambda_resolvability": LAMBDA_RESOLVABILITY,
        "learning_rate": TRAIN_HYPERPARAMS["learning_rate"],
        "loss": loss_contract(),
        "max_epochs": TRAIN_HYPERPARAMS["max_epochs"],
        "max_grad_norm": TRAIN_HYPERPARAMS["max_grad_norm"],
        "max_length": TRAIN_HYPERPARAMS["max_len"],
        "micro_batch_size": TRAIN_HYPERPARAMS["micro_batch_size"],
        "minimum_epochs": TRAIN_HYPERPARAMS["minimum_epochs"],
        "MODEL_WIDE_BEST": BEST_SHA,
        "optimizer": TRAIN_HYPERPARAMS["optimizer"],
        "padding": TRAIN_HYPERPARAMS["padding"],
        "pooling": TRAIN_HYPERPARAMS["pooling"],
        "provenance_weights": dict(PROVENANCE_LOSS_MULTIPLIERS),
        "readiness_sha256": readiness_sha256,
        "relation_class_weights_literal": dict(
            class_weight_artifact["literal_weights"]["relation"]
        ),
        "relation_eligible_identity_list_sha256": class_weight_artifact["relation"][
            "eligible_identity_list_sha256"
        ],
        "relation_masked_identity_list_sha256": class_weight_artifact["relation"][
            "masked_identity_list_sha256"
        ],
        "resolvability_class_weights_literal": dict(
            class_weight_artifact["literal_weights"]["resolvability"]
        ),
        "sampling": {
            "class_balanced_sampler": False,
            "oversampling": False,
            "replacement": False,
            "strategy": "full_pass_deterministic_shuffle",
            "undersampling": False,
        },
        "schema": SCHEMA_CONFIG,
        "seed": TRAIN_HYPERPARAMS["seed"],
        "spent_reserve_status": SPENT_RESERVE_STATUS,
        "spent_reserve": SPENT_RESERVE,
        "spent_reserve_overlap": SPENT_RESERVE_OVERLAP,
        "STAGE_A_BEST_reference_only": PARENT_STAGE_A_BEST_SHA,
        "surface_receipt_sha256": surface_receipt_sha256,
        "surface_rule": AUTHORIZED_SURFACE_RULE,
        "surface_version": AUTHORIZED_SURFACE_VERSION,
        "threshold_grids": {
            "relation_threshold": list(RELATION_THRESHOLDS),
            "resolvability_threshold": list(RESOLVABILITY_THRESHOLDS),
            "n_pairs": 100,
        },
        "threshold_selection": THRESHOLD_SELECTION,
        "tokenizer_identity": tokenizer_identity,
        "train_identity_list_sha256": train_identity_list_sha256,
        "train_split_sha256": train_split_sha256,
        "trainable_layers": TRAIN_HYPERPARAMS["last_trainable"],
        "validation_identity_list_sha256": validation_identity_list_sha256,
        "validation_split_sha256": validation_split_sha256,
        "warmup_ratio": TRAIN_HYPERPARAMS["warmup_ratio"],
        "weight_decay": TRAIN_HYPERPARAMS["weight_decay"],
    }
    config["training_config_sha256"] = sha256_text(
        canonical_json(
            {k: v for k, v in config.items() if k != "training_config_sha256"}
        )
    )
    return config


def factorized_authorization_contract(
    *,
    dataset_sha256: str,
    annotation_sha256: str,
    training_config_sha256: str,
    class_weight_artifact_sha256: str,
    code_revision: str,
    readiness_sha256: str,
    surface_receipt_sha256: str,
    objective_receipt_sha256: str,
) -> dict[str, Any]:
    auth = {
        "AUTHORIZE_RULE": AUTHORIZE_RULE,
        "ANNOTATION_SHA256": annotation_sha256,
        "CLASS_WEIGHT_ARTIFACT_SHA256": class_weight_artifact_sha256,
        "CURRENT_STAGE_A_BEST": PARENT_STAGE_A_BEST_SHA,
        "CURRENT_STAGE_A_BEST_MUTATED": False,
        "DATASET_SHA256": dataset_sha256,
        "DOMAIN_IRRELEVANT_GENERALIZATION": DOMAIN_IRRELEVANT_GENERALIZATION,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "FACTORIZED_OBJECTIVE_SPEC": FACTORIZED_OBJECTIVE_SPEC,
        "MODEL_WIDE_BEST": BEST_SHA,
        "MODEL_WIDE_BEST_MUTATED": False,
        "NEXT_ACTION": TRAIN_ONCE_ACTION,
        "OBJECTIVE_ID": OBJECTIVE_ID,
        "OBJECTIVE_RECEIPT_SHA256": objective_receipt_sha256,
        "PARENT_DECOMPOSITION": PARENT_DECOMPOSITION,
        "POSSIBLE_EVIDENCE_STATUS": POSSIBLE_EVIDENCE_STATUS,
        "READINESS_SHA256": readiness_sha256,
        "SCIENTIFIC_RESULT": "NOT_COMPUTABLE",
        "SPENT_RESERVE": SPENT_RESERVE,
        "SPENT_RESERVE_OVERLAP": SPENT_RESERVE_OVERLAP,
        "SPENT_RESERVE_STATUS": SPENT_RESERVE_STATUS,
        "STAGE_B_MUTATED": False,
        "SURFACE_RECEIPT_SHA256": surface_receipt_sha256,
        "TRAIN_AUTHORIZED": True,
        "TRAINING_CONFIG_SHA256": training_config_sha256,
        "TRAINING_RUN_LIMIT": 1,
        "TRAINING_STATUS": "AUTHORIZED_NOT_STARTED",
        "V1R1_MUTATED": False,
        "V1R2_CREATED": False,
        "code_revision": code_revision,
        "initialization_policy": INITIALIZATION_POLICY,
        "schema": SCHEMA_AUTH,
        "spent_reserve_access_for_train_val_select_threshold_diag": False,
    }
    return auth


def checkpoint_selection_score(
    *, relation_macro_f1: float, resolvability_macro_f1: float
) -> float:
    return 0.50 * float(relation_macro_f1) + 0.50 * float(resolvability_macro_f1)


def select_factorized_checkpoint(candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Tie-break per CHECKPOINT_SELECTION."""
    if not candidates:
        raise ValueError("no_checkpoint_candidates")
    ranked = sorted(
        candidates,
        key=lambda c: (
            -float(c["selection_score"]),
            float(c["relation_false_positive_rate"]),
            -float(c["relation_positive_recall"]),
            -float(c["resolvability_unresolvable_recall"]),
            int(c["epoch"]),
        ),
    )
    return dict(ranked[0])


def calibrate_factorized_thresholds(
    *,
    golds: Sequence[str],
    p_relation: Sequence[float],
    p_resolvable: Sequence[float],
) -> dict[str, Any]:
    """Search 100 threshold pairs; select among acceptance-passing pairs."""
    from .classification_v5_stage_a import evaluate_decisions

    candidates: list[dict[str, Any]] = []
    for r_thr in RELATION_THRESHOLDS:
        for s_thr in RESOLVABILITY_THRESHOLDS:
            decisions = [
                decide_stage_a(
                    p_evidence_relation_present=float(pr),
                    p_resolvable=float(ps),
                    relation_threshold=float(r_thr),
                    resolvability_threshold=float(s_thr),
                )
                for pr, ps in zip(p_relation, p_resolvable)
            ]
            metrics = evaluate_decisions(list(golds), decisions)
            row = {
                "relation_threshold": float(r_thr),
                "resolvability_threshold": float(s_thr),
                "acceptance_pass": bool(metrics["acceptance_pass"]),
                "stage_a_macro_f1": float(metrics["stage_a_macro_f1"]),
                "EVIDENCE_PRESENT_recall": float(
                    metrics["by_label"]["EVIDENCE_PRESENT"]["recall"]
                ),
                "UNCERTAIN_recall": float(metrics["by_label"]["UNCERTAIN"]["recall"]),
                "false_evidence_entry_rate_on_none": float(
                    metrics["false_evidence_entry_rate_on_none"]
                ),
                "metrics": metrics,
            }
            candidates.append(row)
    passing = [c for c in candidates if c["acceptance_pass"]]
    if not passing:
        return {
            "feasible": False,
            "disposition": "SETTLED_FAIL",
            "n_candidates": len(candidates),
            "n_passing": 0,
            "chosen": None,
            "grid": candidates,
        }
    ranked = sorted(
        passing,
        key=lambda c: (
            -float(c["stage_a_macro_f1"]),
            -float(c["EVIDENCE_PRESENT_recall"]),
            -float(c["UNCERTAIN_recall"]),
            float(c["false_evidence_entry_rate_on_none"]),
            -float(c["relation_threshold"]),
            -float(c["resolvability_threshold"]),
        ),
    )
    chosen = ranked[0]
    return {
        "feasible": True,
        "disposition": "SETTLED_PASS",
        "n_candidates": len(candidates),
        "n_passing": len(passing),
        "chosen": {
            "relation_threshold": chosen["relation_threshold"],
            "resolvability_threshold": chosen["resolvability_threshold"],
            "metrics": chosen["metrics"],
        },
        "grid": candidates,
    }


__all__ = [
    "AUTHORIZE_RULE",
    "CHECKPOINT_SELECTION",
    "CLASS_WEIGHT_FORMULA_VERSION",
    "CLASS_WEIGHT_RESOLUTION_RULE",
    "EXPERIMENT_ID",
    "INITIALIZATION_POLICY",
    "THRESHOLD_SELECTION",
    "TRAIN_ONCE_ACTION",
    "TRAIN_RULE",
    "calibrate_factorized_thresholds",
    "checkpoint_selection_score",
    "decide_stage_a",
    "factorized_authorization_contract",
    "factorized_resolved_config",
    "identity_list_sha256",
    "load_annotation_index",
    "provenance_multiplier",
    "relation_loss_eligible",
    "resolve_factorized_relation_class_weights",
    "select_factorized_checkpoint",
    "verify_v1r1_split_pins",
]
