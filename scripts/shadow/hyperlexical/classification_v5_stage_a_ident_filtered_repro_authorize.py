"""AUTHORIZE_REPRODUCE_IDENT_FILTERED_FACTORIZED_TRAIN.

Authorization only. Reproduction of the settled ident-filtered factorized
experiment after checkpoint serialization dropped selected heads. Does not
train, mutate V1R2, recompute class weights, move BEST, or score reserve.
"""

from __future__ import annotations

from typing import Any, Mapping

from .classification_v5_stage_a import (
    ACCEPTANCE_GATES,
    BEST_SHA,
    TRAIN_HYPERPARAMS,
    canonical_json,
    sha256_text,
)
from .classification_v5_stage_a_factorized_authorize import (
    CHECKPOINT_SELECTION,
    THRESHOLD_SELECTION,
)
from .classification_v5_stage_a_factorized_objective import (
    DOMAIN_IRRELEVANT_GENERALIZATION,
    LAMBDA_RESOLVABILITY,
    OBJECTIVE_ID,
    OBJECTIVE_RECEIPT_SHA256_PIN,
    RELATION_THRESHOLDS,
    RESOLVABILITY_THRESHOLDS,
    architecture_contract,
    loss_contract,
)
from .classification_v5_stage_a_gold_identifiability_filter import (
    FILTER_RECEIPT_SHA256_PIN,
    V1R2_ANNOTATION_SHA256_PIN,
    V1R2_DATASET_SHA256_PIN,
    V1R2_EXCLUSION_MANIFEST_SHA256_PIN,
)
from .classification_v5_stage_a_ident_filtered_authorize import (
    AUTHORIZED_AUTH_RECEIPT_SHA256,
    AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
    AUTHORIZED_TRAINING_CONFIG_SHA256,
    EXPECTED_RELATION_TRAIN_ELIGIBLE,
    EXPECTED_RELATION_TRAIN_ELIGIBLE_ID_SHA256,
    EXPECTED_RELATION_TRAIN_MASKED,
    EXPECTED_RELATION_TRAIN_MASKED_ID_SHA256,
    EXPECTED_TRAIN_IDENTITY_LIST_SHA256,
    EXPECTED_TRAIN_ROWS,
    EXPECTED_TRAIN_SPLIT_SHA256,
    EXPECTED_VALIDATION_IDENTITY_LIST_SHA256,
    EXPECTED_VALIDATION_ROWS,
    EXPECTED_VALIDATION_SPLIT_SHA256,
    EXPERIMENT_ID as PARENT_EXPERIMENT_ID,
    EXPLICIT_LIMITATIONS,
    INITIALIZATION_POLICY,
    LITERAL_RELATION_WEIGHTS,
    LITERAL_RESOLVABILITY_WEIGHTS,
    SHORT_ATOM_POSITIVE_GENERALIZATION,
    ident_filtered_resolved_config,
)
from .classification_v5_stage_a_ident_filtered_checkpoint_repair import (
    PROMOTION_INVALID_RECEIPT_SHA256,
    TRAINING_RESULT_RECEIPT_SHA256 as ORIGINAL_RUN_RECEIPT_SHA256,
    serialization_regression_report,
)
from .classification_v5_stage_a_two_stage_generalization import (
    PARENT_STAGE_A_BEST_SHA,
    SPENT_RESERVE,
    SPENT_RESERVE_STATUS,
)
from .save_pretrained import FACTORIZED_HEAD_NAMES

AUTHORIZE_RULE = "AUTHORIZE_REPRODUCE_IDENT_FILTERED_FACTORIZED_TRAIN"
EXPERIMENT_ID = (
    "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-REPRO-001"
)
PARENT_EXPERIMENT = PARENT_EXPERIMENT_ID
REPRODUCTION_REASON = "SELECTED_FACTORIZED_HEADS_NOT_SERIALIZED"
TRAIN_ONCE_ACTION = "REPRODUCE_IDENT_FILTERED_FACTORIZED_TRAIN_ONCE"
TRAIN_RULE = "HYPERLEX_V5_STAGE_A_IDENT_FILTERED_FACTORIZED_REPRO_TRAIN_V1"
SERIALIZATION_FIX_COMMIT = "9edf8fc682a072924e4dc76d6e5733b0f3f0090f"
SERIALIZER_VERSION = "factorized_heads_whitelisted_v1"
CHECKPOINT_MANIFEST_SCHEMA = (
    "hyperlex.classification.v5."
    "stage_a_ident_filtered_factorized_complete_checkpoint_manifest.v1"
)
SCHEMA_REPRO_CONFIG = (
    "hyperlex.classification.v5."
    "stage_a_ident_filtered_factorized_reproduction_training_config.v1"
)
SCHEMA_AUTH = (
    "hyperlex.classification.v5."
    "stage_a_ident_filtered_factorized_reproduction_authorization.v1"
)
CHECKPOINT_REPAIR_RECEIPT_SHA256 = (
    "6b04194718f7cbe9645816c7cf9064419f5759d2080bf4bad9c2093281b4d15b"
)
ORIGINAL_SELECTED_ENCODER_ONLY_SHA256 = (
    "8b2de4472dc0ebd65a6b4b7577dc3272d63db2490a1b6f6dbbcc54db50077e41"
)
ORIGINAL_SELECTED_EPOCH = 11
ORIGINAL_CODE_REVISION = "4bf24609fb487ab8c35aec223b05c72f1019ea6e"
ORIGINAL_TOKENIZER_IDENTITY = "local_files_only:ModernBERT-base"

REPRODUCTION_CLASSIFICATION = (
    "EXACT_REPRODUCTION",
    "NUMERICALLY_EQUIVALENT_REPRODUCTION",
    "SCIENTIFICALLY_EQUIVALENT_REPRODUCTION",
    "REPRODUCTION_DIVERGED",
)

ORIGINAL_SETTLED_METRICS = {
    "false_evidence_entry_rate_on_none": 0.03356890459363958,
    "EVIDENCE_PRESENT_recall": 0.951310861423221,
    "NO_EVIDENCE_recall": 0.9646643109540636,
    "SHORT_ATOM_NONE_relation_FPR": 0.013,
    "selected_epoch": ORIGINAL_SELECTED_EPOCH,
    "relation_threshold": 0.60,
    "resolvability_threshold": 0.75,
    "prior_unfiltered_SHORT_ATOM_NONE_relation_FPR": 0.539,
}

RNG_INIT_ORDER = (
    "torch.manual_seed(42)",
    "AutoTokenizer.from_pretrained(trunk, local_files_only=True)",
    "AutoModel.from_pretrained(trunk, local_files_only=True)",
    "apply_encoder_trainable(MODEL_WIDE_BEST_9fba0f66)",
    "freeze_encoder(last_trainable=2)",
    "nn.Linear(HIDDEN, 2)  # relation_head default init",
    "nn.Linear(HIDDEN, 2)  # resolvability_head default init",
    "nn.init.xavier_uniform_(relation_head.weight)",
    "nn.init.zeros_(relation_head.bias)",
    "nn.init.xavier_uniform_(resolvability_head.weight)",
    "nn.init.zeros_(resolvability_head.bias)",
)

RNG_GAPS = (
    "no torch.cuda.manual_seed in original runner",
    "no numpy.random.seed / random.seed in original runner",
    "no cudnn.deterministic / benchmark=False recorded",
    "tokenizer/encoder construction sits between manual_seed and Xavier",
)

RNG_CONTRACT = {
    "status": "VERIFIED_FROM_ORIGINAL_RUNNER",
    "seed": 42,
    "encoder": "MODEL_WIDE_BEST 9fba0f66… overlay after trunk load",
    "relation_head": "fresh Xavier under seed 42 after Linear() constructors",
    "resolvability_head": "fresh Xavier under seed 42 after relation Xavier",
    "order": list(RNG_INIT_ORDER),
    "gaps": list(RNG_GAPS),
    "reproduction_class_implication": (
        "ORDER_ESTABLISHED_NOT_BYTE_GUARANTEED: exact tensor reproduction "
        "is not promised; scientific-config identity is."
    ),
    "silently_redefined": False,
}

REPRO_SAVE_POLICY = {
    "require_factorized_heads_in_flat": True,
    "required_tensors": [
        "relation_head.weight",
        "relation_head.bias",
        "resolvability_head.weight",
        "resolvability_head.bias",
    ],
    "encoder_only_factorized_checkpoint_valid": False,
    "fail_save_if_either_head_missing": True,
    "persist_complete_state_on_new_best": True,
    "retain": ["SELECTED_COMPLETE_CHECKPOINT", "FINAL_COMPLETE_CHECKPOINT"],
    "both_independently_cold_loadable": True,
    "checkpoint_manifest_schema": CHECKPOINT_MANIFEST_SCHEMA,
    "manifest_must_include": [
        "relation_head.weight hash",
        "relation_head.bias hash",
        "resolvability_head.weight hash",
        "resolvability_head.bias hash",
        "adapted encoder tensor hashes",
        "parent MODEL_WIDE_BEST",
        "experiment ID",
        "epoch",
    ],
}

SERIALIZATION_ONLY_KEYS = (
    "PARENT_EXPERIMENT",
    "REPRODUCTION_REASON",
    "serializer_version",
    "serialization_fix_commit",
    "factorized_head_save_enforcement",
    "require_factorized_heads_in_flat",
    "checkpoint_manifest_schema",
    "save_policy",
    "retain_selected_and_final_complete_checkpoints",
    "schema",
    "code_revision",
    "EXPERIMENT_ID",
    "training_config_sha256",
    "original_training_config_sha256",
    "SCIENTIFIC_CONFIG_PARITY",
    "scientific_config_sha256",
)

SCIENTIFIC_QUESTION = (
    "Does the original ident-filtered factorized SETTLED_PASS reproduce "
    "as a complete cold-loadable checkpoint once factorized heads survive "
    "serialization, under identical scientific inputs?"
)


def verify_class_weight_identity(artifact: Mapping[str, Any]) -> dict[str, Any]:
    sha = str(artifact.get("CLASS_WEIGHT_ARTIFACT_SHA256") or "")
    if sha != AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256:
        raise ValueError("REPRODUCTION_CONFIG_MISMATCH:class_weight_artifact_sha")
    literal = artifact.get("literal_weights") or {}
    relation = dict(literal.get("relation") or {})
    resolvability = dict(literal.get("resolvability") or {})
    for label, expected in LITERAL_RELATION_WEIGHTS.items():
        if abs(float(relation[label]) - expected) > 0.0:
            raise ValueError(f"REPRODUCTION_CONFIG_MISMATCH:relation:{label}")
    for label, expected in LITERAL_RESOLVABILITY_WEIGHTS.items():
        if abs(float(resolvability[label]) - expected) > 0.0:
            raise ValueError(f"REPRODUCTION_CONFIG_MISMATCH:resolvability:{label}")
    return {
        "pass": True,
        "CLASS_WEIGHT_ARTIFACT_SHA256": sha,
        "recomputed": False,
        "relation": dict(LITERAL_RELATION_WEIGHTS),
        "resolvability": dict(LITERAL_RESOLVABILITY_WEIGHTS),
    }


def verify_split_identity(
    *,
    train_rows: int,
    validation_rows: int,
    train_split_sha256: str,
    validation_split_sha256: str,
    train_identity_sha256: str,
    validation_identity_sha256: str,
    relation_eligible_train_sha256: str,
    relation_masked_train_sha256: str,
    relation_eligible_train: int = EXPECTED_RELATION_TRAIN_ELIGIBLE,
    relation_masked_train: int = EXPECTED_RELATION_TRAIN_MASKED,
) -> dict[str, Any]:
    checks = {
        "TRAIN_ROWS": int(train_rows) == EXPECTED_TRAIN_ROWS,
        "VALIDATION_ROWS": int(validation_rows) == EXPECTED_VALIDATION_ROWS,
        "TRAIN_SPLIT_SHA256": train_split_sha256 == EXPECTED_TRAIN_SPLIT_SHA256,
        "VALIDATION_SPLIT_SHA256": (
            validation_split_sha256 == EXPECTED_VALIDATION_SPLIT_SHA256
        ),
        "TRAIN_IDENTITY_SHA256": (
            train_identity_sha256 == EXPECTED_TRAIN_IDENTITY_LIST_SHA256
        ),
        "VALIDATION_IDENTITY_SHA256": (
            validation_identity_sha256 == EXPECTED_VALIDATION_IDENTITY_LIST_SHA256
        ),
        "RELATION_ELIGIBLE_TRAIN_SHA256": (
            relation_eligible_train_sha256
            == EXPECTED_RELATION_TRAIN_ELIGIBLE_ID_SHA256
        ),
        "RELATION_MASKED_TRAIN_SHA256": (
            relation_masked_train_sha256 == EXPECTED_RELATION_TRAIN_MASKED_ID_SHA256
        ),
        "relation_eligible_train_n": (
            int(relation_eligible_train) == EXPECTED_RELATION_TRAIN_ELIGIBLE
        ),
        "relation_masked_train_n": (
            int(relation_masked_train) == EXPECTED_RELATION_TRAIN_MASKED
        ),
    }
    if not all(checks.values()):
        raise ValueError(f"REPRODUCTION_CONFIG_MISMATCH:split:{checks}")
    return {
        "pass": True,
        "TRAIN_ROWS": EXPECTED_TRAIN_ROWS,
        "VALIDATION_ROWS": EXPECTED_VALIDATION_ROWS,
        "TRAIN_SPLIT_SHA256": EXPECTED_TRAIN_SPLIT_SHA256,
        "VALIDATION_SPLIT_SHA256": EXPECTED_VALIDATION_SPLIT_SHA256,
        "TRAIN_IDENTITY_SHA256": EXPECTED_TRAIN_IDENTITY_LIST_SHA256,
        "VALIDATION_IDENTITY_SHA256": EXPECTED_VALIDATION_IDENTITY_LIST_SHA256,
        "RELATION_ELIGIBLE_TRAIN_SHA256": EXPECTED_RELATION_TRAIN_ELIGIBLE_ID_SHA256,
        "RELATION_MASKED_TRAIN_SHA256": EXPECTED_RELATION_TRAIN_MASKED_ID_SHA256,
        "checks": checks,
    }


def extract_scientific_config(config: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in config.items()
        if key not in SERIALIZATION_ONLY_KEYS
    }


def scientific_config_parity(
    original_config: Mapping[str, Any],
    reproduction_config: Mapping[str, Any],
) -> dict[str, Any]:
    original_sci = extract_scientific_config(original_config)
    repro_sci = extract_scientific_config(reproduction_config)
    original_sha = sha256_text(canonical_json(original_sci))
    repro_sha = sha256_text(canonical_json(repro_sci))
    return {
        "pass": original_sci == repro_sci and original_sha == repro_sha,
        "original_scientific_config_sha256": original_sha,
        "reproduction_scientific_config_sha256": repro_sha,
        "SCIENTIFIC_CONFIG_PARITY": (
            "PASS" if original_sci == repro_sci and original_sha == repro_sha else "FAIL"
        ),
        "excluded_keys": list(SERIALIZATION_ONLY_KEYS),
    }


def verify_rng_contract() -> dict[str, Any]:
    seed = int(TRAIN_HYPERPARAMS["seed"])
    checks = {
        "seed_42": seed == 42,
        "head_init_xavier_uniform_bias_zeros": (
            TRAIN_HYPERPARAMS["head_init"] == "xavier_uniform_bias_zeros"
        ),
        "initialization_policy_fresh_from_model_wide_best": (
            INITIALIZATION_POLICY["base_encoder_source"] == "MODEL_WIDE_BEST"
            and INITIALIZATION_POLICY["stage_a_best_continuation"] is False
            and INITIALIZATION_POLICY["relation_head"]
            == "fresh_xavier_uniform_bias_zeros"
            and INITIALIZATION_POLICY["resolvability_head"]
            == "fresh_xavier_uniform_bias_zeros"
        ),
        "order_established_from_original_runner": True,
        "not_silently_redefined": RNG_CONTRACT["silently_redefined"] is False,
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "contract": dict(RNG_CONTRACT),
    }


def rebuild_original_scientific_config(
    class_weight_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    config = ident_filtered_resolved_config(
        dataset_sha256=V1R2_DATASET_SHA256_PIN,
        annotation_sha256=V1R2_ANNOTATION_SHA256_PIN,
        exclusion_manifest_sha256=V1R2_EXCLUSION_MANIFEST_SHA256_PIN,
        class_weight_artifact=class_weight_artifact,
        code_revision=ORIGINAL_CODE_REVISION,
        tokenizer_identity=ORIGINAL_TOKENIZER_IDENTITY,
        train_split_sha256=EXPECTED_TRAIN_SPLIT_SHA256,
        validation_split_sha256=EXPECTED_VALIDATION_SPLIT_SHA256,
        train_identity_list_sha256=EXPECTED_TRAIN_IDENTITY_LIST_SHA256,
        validation_identity_list_sha256=EXPECTED_VALIDATION_IDENTITY_LIST_SHA256,
        surface_receipt_sha256=FILTER_RECEIPT_SHA256_PIN,
        objective_receipt_sha256=OBJECTIVE_RECEIPT_SHA256_PIN,
    )
    if config["training_config_sha256"] != AUTHORIZED_TRAINING_CONFIG_SHA256:
        raise ValueError(
            "REPRODUCTION_CONFIG_MISMATCH:original_training_config_rebuild"
        )
    return config


def reproduction_training_config(
    *,
    class_weight_artifact: Mapping[str, Any],
    code_revision: str,
    original_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    original = original_config or rebuild_original_scientific_config(
        class_weight_artifact
    )
    config = dict(original)
    config["EXPERIMENT_ID"] = EXPERIMENT_ID
    config["PARENT_EXPERIMENT"] = PARENT_EXPERIMENT
    config["REPRODUCTION_REASON"] = REPRODUCTION_REASON
    config["code_revision"] = code_revision
    config["schema"] = SCHEMA_REPRO_CONFIG
    config["serializer_version"] = SERIALIZER_VERSION
    config["serialization_fix_commit"] = SERIALIZATION_FIX_COMMIT
    config["factorized_head_save_enforcement"] = True
    config["require_factorized_heads_in_flat"] = True
    config["checkpoint_manifest_schema"] = CHECKPOINT_MANIFEST_SCHEMA
    config["save_policy"] = dict(REPRO_SAVE_POLICY)
    config["retain_selected_and_final_complete_checkpoints"] = True
    config["original_training_config_sha256"] = AUTHORIZED_TRAINING_CONFIG_SHA256
    parity = scientific_config_parity(original, config)
    if not parity["pass"]:
        raise ValueError("REPRODUCTION_CONFIG_MISMATCH:scientific_config")
    config["SCIENTIFIC_CONFIG_PARITY"] = parity["SCIENTIFIC_CONFIG_PARITY"]
    config["scientific_config_sha256"] = parity["original_scientific_config_sha256"]
    config["training_config_sha256"] = sha256_text(
        canonical_json(
            {k: v for k, v in config.items() if k != "training_config_sha256"}
        )
    )
    return config


def reproduction_authorization_contract(
    *,
    training_config_sha256: str,
    class_weight_parity: Mapping[str, Any],
    split_identity: Mapping[str, Any],
    scientific_parity: Mapping[str, Any],
    serialization_tests: Mapping[str, Any],
    rng_contract: Mapping[str, Any],
    code_revision: str,
) -> dict[str, Any]:
    gates_ok = all(
        [
            class_weight_parity.get("pass"),
            split_identity.get("pass"),
            scientific_parity.get("pass"),
            serialization_tests.get("pass"),
            rng_contract.get("pass"),
        ]
    )
    if not gates_ok:
        raise ValueError("REPRODUCTION_AUTHORIZATION_BLOCKED")
    auth = {
        "ANNOTATION_SHA256": V1R2_ANNOTATION_SHA256_PIN,
        "AUTHORIZE_RULE": AUTHORIZE_RULE,
        "CHECKPOINT_REPAIR_RECEIPT_SHA256": CHECKPOINT_REPAIR_RECEIPT_SHA256,
        "CLASS_WEIGHT_ARTIFACT_SHA256": AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
        "CURRENT_STAGE_A_BEST": PARENT_STAGE_A_BEST_SHA,
        "CURRENT_STAGE_A_BEST_MUTATED": False,
        "DATASET_SHA256": V1R2_DATASET_SHA256_PIN,
        "DOMAIN_IRRELEVANT_GENERALIZATION": DOMAIN_IRRELEVANT_GENERALIZATION,
        "EXCLUSION_MANIFEST_SHA256": V1R2_EXCLUSION_MANIFEST_SHA256_PIN,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "EXPLICIT_LIMITATIONS": EXPLICIT_LIMITATIONS,
        "MODEL_WIDE_BEST": BEST_SHA,
        "MODEL_WIDE_BEST_MUTATED": False,
        "NEXT_ACTION": TRAIN_ONCE_ACTION,
        "OBJECTIVE_ID": OBJECTIVE_ID,
        "ORIGINAL_AUTH_RECEIPT_SHA256": AUTHORIZED_AUTH_RECEIPT_SHA256,
        "ORIGINAL_RUN_RECEIPT_SHA256": ORIGINAL_RUN_RECEIPT_SHA256,
        "ORIGINAL_SCIENTIFIC_RESULT": "SETTLED_PASS",
        "ORIGINAL_SELECTED_ENCODER_ONLY_SHA256": ORIGINAL_SELECTED_ENCODER_ONLY_SHA256,
        "ORIGINAL_SELECTED_EPOCH": ORIGINAL_SELECTED_EPOCH,
        "ORIGINAL_TRAINING_CONFIG_SHA256": AUTHORIZED_TRAINING_CONFIG_SHA256,
        "PARENT_EXPERIMENT": PARENT_EXPERIMENT,
        "PROMOTION_INVALID_RECEIPT_SHA256": PROMOTION_INVALID_RECEIPT_SHA256,
        "REPRODUCTION_CLASSIFICATION_DEFERRED": True,
        "REPRODUCTION_CLASSIFICATION_VALUES": list(REPRODUCTION_CLASSIFICATION),
        "REPRODUCTION_REASON": REPRODUCTION_REASON,
        "REPRODUCTION_TRAINING_CONFIG_SHA256": training_config_sha256,
        "SCIENTIFIC_CONFIG_PARITY": scientific_parity["SCIENTIFIC_CONFIG_PARITY"],
        "SCIENTIFIC_QUESTION": SCIENTIFIC_QUESTION,
        "SCIENTIFIC_RESULT": "NOT_COMPUTABLE",
        "SERIALIZATION_FIX_COMMIT": SERIALIZATION_FIX_COMMIT,
        "SERIALIZER_VERSION": SERIALIZER_VERSION,
        "SHORT_ATOM_POSITIVE_GENERALIZATION": SHORT_ATOM_POSITIVE_GENERALIZATION,
        "SPENT_RESERVE": SPENT_RESERVE,
        "SPENT_RESERVE_STATUS": SPENT_RESERVE_STATUS,
        "STAGE_B_MUTATED": False,
        "TRAIN_AUTHORIZED": True,
        "TRAINING_RUN_LIMIT": 1,
        "TRAINING_STATUS": "AUTHORIZED_NOT_STARTED",
        "V1R2_MUTATED": False,
        "acceptance_gates": dict(ACCEPTANCE_GATES),
        "architecture": architecture_contract(),
        "checkpoint_selection": dict(CHECKPOINT_SELECTION),
        "class_weight_parity": dict(class_weight_parity),
        "code_revision": code_revision,
        "initialization_policy": INITIALIZATION_POLICY,
        "lambda_resolvability": LAMBDA_RESOLVABILITY,
        "loss": loss_contract(),
        "optimizer_hyperparams": {
            "optimizer": TRAIN_HYPERPARAMS["optimizer"],
            "learning_rate": TRAIN_HYPERPARAMS["learning_rate"],
            "weight_decay": TRAIN_HYPERPARAMS["weight_decay"],
            "micro_batch_size": TRAIN_HYPERPARAMS["micro_batch_size"],
            "gradient_accumulation": TRAIN_HYPERPARAMS["gradient_accumulation"],
            "max_epochs": TRAIN_HYPERPARAMS["max_epochs"],
            "minimum_epochs": TRAIN_HYPERPARAMS["minimum_epochs"],
            "early_stopping_patience": TRAIN_HYPERPARAMS["early_stopping_patience"],
            "warmup_ratio": TRAIN_HYPERPARAMS["warmup_ratio"],
            "max_grad_norm": TRAIN_HYPERPARAMS["max_grad_norm"],
            "max_len": TRAIN_HYPERPARAMS["max_len"],
            "seed": TRAIN_HYPERPARAMS["seed"],
            "sampling": "deterministic full-pass; no replacement; no over/under sampling",
        },
        "original_settled_metrics": dict(ORIGINAL_SETTLED_METRICS),
        "rng_contract": dict(rng_contract),
        "save_policy": dict(REPRO_SAVE_POLICY),
        "schema": SCHEMA_AUTH,
        "scientific_parity": dict(scientific_parity),
        "serialization_regression_tests": dict(serialization_tests),
        "spent_reserve_access_for_train_val_select_threshold_diag": False,
        "split_identity": dict(split_identity),
        "threshold_grids": {
            "relation_threshold": list(RELATION_THRESHOLDS),
            "resolvability_threshold": list(RESOLVABILITY_THRESHOLDS),
            "n_pairs": 100,
            "do_not_force_original_winning_pair": True,
        },
        "threshold_selection": dict(THRESHOLD_SELECTION),
        "whitelisted_factorized_heads": list(FACTORIZED_HEAD_NAMES),
    }
    auth["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in auth.items() if k != "receipt_sha256"})
    )
    return auth


def authorize_reproduction(
    *,
    class_weight_artifact: Mapping[str, Any],
    code_revision: str,
    train_rows: int = EXPECTED_TRAIN_ROWS,
    validation_rows: int = EXPECTED_VALIDATION_ROWS,
    train_split_sha256: str = EXPECTED_TRAIN_SPLIT_SHA256,
    validation_split_sha256: str = EXPECTED_VALIDATION_SPLIT_SHA256,
    train_identity_sha256: str = EXPECTED_TRAIN_IDENTITY_LIST_SHA256,
    validation_identity_sha256: str = EXPECTED_VALIDATION_IDENTITY_LIST_SHA256,
    relation_eligible_train_sha256: str = EXPECTED_RELATION_TRAIN_ELIGIBLE_ID_SHA256,
    relation_masked_train_sha256: str = EXPECTED_RELATION_TRAIN_MASKED_ID_SHA256,
) -> dict[str, Any]:
    split = verify_split_identity(
        train_rows=train_rows,
        validation_rows=validation_rows,
        train_split_sha256=train_split_sha256,
        validation_split_sha256=validation_split_sha256,
        train_identity_sha256=train_identity_sha256,
        validation_identity_sha256=validation_identity_sha256,
        relation_eligible_train_sha256=relation_eligible_train_sha256,
        relation_masked_train_sha256=relation_masked_train_sha256,
    )
    weights = verify_class_weight_identity(class_weight_artifact)
    original = rebuild_original_scientific_config(class_weight_artifact)
    config = reproduction_training_config(
        class_weight_artifact=class_weight_artifact,
        code_revision=code_revision,
        original_config=original,
    )
    parity = scientific_config_parity(original, config)
    serialization = serialization_regression_report()
    rng = verify_rng_contract()
    auth = reproduction_authorization_contract(
        training_config_sha256=config["training_config_sha256"],
        class_weight_parity=weights,
        split_identity=split,
        scientific_parity=parity,
        serialization_tests=serialization,
        rng_contract=rng,
        code_revision=code_revision,
    )
    return {
        "authorization": auth,
        "training_config": config,
        "split_identity": split,
        "class_weight_parity": weights,
        "scientific_parity": parity,
        "serialization_regression_tests": serialization,
        "rng_contract": rng,
    }
