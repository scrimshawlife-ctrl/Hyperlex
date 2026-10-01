"""AUTHORIZE_STAGE_A_IDENT_FILTERED_FACTORIZED_TRAIN — auth + class weights.

Authorizes one fresh factorized train on V1R2 (identifiability-filtered).
Does not train, mutate V1R2, restore excluded rows, relabel, alter Stage B,
access spent reserve, or move BEST.
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
from .classification_v5_stage_a_factorized_authorize import (
    CHECKPOINT_SELECTION,
    THRESHOLD_SELECTION,
)
from .classification_v5_stage_a_factorized_objective import (
    DOMAIN_IRRELEVANT_GENERALIZATION,
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
    loss_contract,
)
from .classification_v5_stage_a_gold_identifiability_filter import (
    CONTRACT_RECEIPT_SHA256_PIN,
    DATASET_VERSION,
    FILTER_ID,
    FILTER_RECEIPT_SHA256_PIN,
    FILTER_RULE,
    PARENT_DATASET_SHA256,
    SURFACE_ID,
    V1R2_ANNOTATION_SHA256_PIN,
    V1R2_DATASET_SHA256_PIN,
    V1R2_EXCLUSION_MANIFEST_SHA256_PIN,
)
from .classification_v5_stage_a_two_stage import (
    DROP_LAST,
    _account_row,
    _empty_class_account,
    _finalize_binary_accounts,
    full_pass_batch_indices,
    identity_list_sha256,
    split_lines_sha256,
)
from .classification_v5_stage_a_two_stage_generalization import (
    PARENT_STAGE_A_BEST_SHA,
    SPENT_RESERVE,
    SPENT_RESERVE_OVERLAP,
    SPENT_RESERVE_STATUS,
)

AUTHORIZE_RULE = "AUTHORIZE_STAGE_A_IDENT_FILTERED_FACTORIZED_TRAIN"
CLASS_WEIGHT_RESOLUTION_RULE = "RESOLVE_STAGE_A_IDENT_FILTERED_FACTORIZED_CLASS_WEIGHTS"
CLASS_WEIGHT_FORMULA_VERSION = (
    "HYPERLEX_V5_IDENT_FILTERED_FACTORIZED_CLASS_WEIGHTS_V1"
)
EXPERIMENT_ID = (
    "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-001"
)
TRAIN_ONCE_ACTION = "TRAIN_STAGE_A_IDENT_FILTERED_FACTORIZED_ONCE"
TRAIN_RULE = "HYPERLEX_V5_STAGE_A_IDENT_FILTERED_FACTORIZED_TRAIN_V1"
SCIENTIFIC_QUESTION = (
    "Does the existing factorized relation/resolvability objective "
    "become learnable once supervision is restricted to gold "
    "that is identifiable from the model-visible text?"
)

SCHEMA_CLASS_WEIGHTS = (
    "hyperlex.classification.v5."
    "stage_a_ident_filtered_factorized_class_weights.v1"
)
SCHEMA_AUTH = (
    "hyperlex.classification.v5."
    "stage_a_ident_filtered_factorized_authorization.v1"
)
SCHEMA_CONFIG = (
    "hyperlex.classification.v5."
    "stage_a_ident_filtered_factorized_training_config.v1"
)

# V1R2 sealed membership / split pins (computed from V1R2 artifacts).
EXPECTED_V1R2_ROWS = 3120
EXPECTED_EXCLUDED_ROWS = 465
EXPECTED_PARENT_ROWS = 3585
EXPECTED_TRAIN_ROWS = 2272
EXPECTED_VALIDATION_ROWS = 848
EXPECTED_TRAIN_SPLIT_SHA256 = (
    "d0eb1f10329d859bbc51a9774727442f455e9b2dab030b21dcd871d31f396727"
)
EXPECTED_VALIDATION_SPLIT_SHA256 = (
    "52f234ce807f1e67fd6b896ecdd45c733cf146bd1dc9b25f98fbd93809a9f8e2"
)
EXPECTED_TRAIN_IDENTITY_LIST_SHA256 = (
    "69ef5c7813c2666ec21dd770423f8f82caa661edc91841af00e95e3e47f886d7"
)
EXPECTED_VALIDATION_IDENTITY_LIST_SHA256 = (
    "03add594c4f2e1e96d1c094a3ac9c45775bc02ebf80faa0ed7c840a7da44290c"
)
EXPECTED_RELATION_ELIGIBLE_TOTAL = 3066
EXPECTED_RELATION_MASKED_TOTAL = 54
EXPECTED_RELATION_TRAIN_ELIGIBLE = 2233
EXPECTED_RELATION_TRAIN_MASKED = 39
EXPECTED_RELATION_TRAIN_ELIGIBLE_ID_SHA256 = (
    "2ac99867ae66d9c3c0b8e30227df11c5da5dfc4caa190dbc4ae667df78954ad4"
)
EXPECTED_RELATION_TRAIN_MASKED_ID_SHA256 = (
    "77b431716025dbf9d944c862003f5f439ac29f1801dcfaa336f587177ddbccbf"
)
EXPECTED_OPTIMIZER_STEPS_PER_EPOCH = 284  # ceil(2272/8)

SHORT_ATOM_POSITIVE_GENERALIZATION = "LOW_SUPPORT"
SHORT_ATOM_PRESENT_SUPPORT_V1R2 = 11
SHORT_ATOM_NONE_SUPPORT_V1R2 = 310

# Sealed by AUTHORIZE_STAGE_A_IDENT_FILTERED_FACTORIZED_TRAIN.
AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256 = (
    "13e8d0ca250839500b71b4b9e23d8238a90488987b9a49cd2c6d2fc336f77fc6"
)
AUTHORIZED_TRAINING_CONFIG_SHA256 = (
    "e252f1ba7beb577f0beb90bc9de294a16a8b808508081bb5b081b530fcaab460"
)
AUTHORIZED_AUTH_RECEIPT_SHA256 = (
    "6341d0831327bdc3c912b133025b7265c62986badf369819d44dcaf506da42ed"
)

LITERAL_RELATION_WEIGHTS: dict[str, float] = {
    "NO_EVIDENCE_RELATION": 0.8985774732156429,
    "EVIDENCE_RELATION_PRESENT": 1.1014225267843571,
}
LITERAL_RESOLVABILITY_WEIGHTS: dict[str, float] = {
    "UNRESOLVABLE": 1.7030222347950057,
    "RESOLVABLE": 0.5,
}

INITIALIZATION_POLICY = {
    "base_encoder_sha256": BEST_SHA,
    "base_encoder_source": "MODEL_WIDE_BEST",
    "conflict_with_stage_a_best_continuation": False,
    "forbidden_initializations": [
        "STAGE_A_BEST_cd2829c1",
        "failed_factorized_8a6981c1",
        "failed_two_stage_26841d5f",
    ],
    "head_init": TRAIN_HYPERPARAMS["head_init"],
    "last_two_encoder_layers_source": "MODEL_WIDE_BEST_overlay",
    "policy": (
        "FRESH_RETRAIN_FROM_MODEL_WIDE_BEST:"
        "encoder_overlay_from_9fba0f66; "
        "relation_head/resolvability_head freshly Xavier-initialized; "
        "do_not_load_STAGE_A_BEST_or_prior_failed_ckpts"
    ),
    "relation_head": "fresh_xavier_uniform_bias_zeros",
    "resolvability_head": "fresh_xavier_uniform_bias_zeros",
    "scientific_interpretation": (
        "Ident-filtered factorized objective fresh retrain from MODEL_WIDE_BEST "
        "on V1R2; tests gold-contract repair only."
    ),
    "stage_a_best_continuation": False,
    "stage_a_best_sha256_reference_only": PARENT_STAGE_A_BEST_SHA,
    "trunk": "ModernBERT-base",
}

IDENTIFIABILITY_DIAGNOSTIC_CONTRACT = {
    "SHORT_ATOM_NONE": {
        "report": ["support", "relation_FPR", "NONE_recall"],
    },
    "SHORT_ATOM_PRESENT": {
        "report": ["support", "relation_recall", "low_support_warning"],
        "support_v1r2": SHORT_ATOM_PRESENT_SUPPORT_V1R2,
        "stable_subgroup_guarantee": False,
    },
    "also_report": [
        "TEXT_IDENTIFIABLE_relation_rows",
        "genuine_UNCERTAIN_rows",
        "OBSERVED_INFERRED",
        "source_family",
        "domain",
        "length_band",
    ],
    "compare_read_only_prior_factorized": {
        "false_entry": 0.180,
        "NONE_recall": 0.807,
        "PRESENT_recall": 0.888,
        "SHORT_ATOM_NONE_relation_FPR": 0.539,
        "formal_acceptance_gates": False,
    },
}

EXPLICIT_LIMITATIONS = {
    "DOMAIN_IRRELEVANT_GENERALIZATION": DOMAIN_IRRELEVANT_GENERALIZATION,
    "SHORT_ATOM_POSITIVE_GENERALIZATION": SHORT_ATOM_POSITIVE_GENERALIZATION,
    "SHORT_ATOM_PRESENT_SUPPORT": SHORT_ATOM_PRESENT_SUPPORT_V1R2,
    "note": (
        "Passing aggregate gates must not be described as establishing "
        "broad short-atom positive generalization."
    ),
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


def verify_exclusion_integrity(
    *,
    v1r2_identities: Sequence[str],
    exclusion_identities: Sequence[str],
) -> dict[str, Any]:
    kept = set(str(x) for x in v1r2_identities)
    excluded = set(str(x) for x in exclusion_identities)
    overlap = kept & excluded
    if overlap:
        raise ValueError(f"EXCLUSION_OVERLAP:{len(overlap)}")
    if len(kept) != EXPECTED_V1R2_ROWS:
        raise ValueError(f"kept_count_mismatch:{len(kept)}")
    if len(excluded) != EXPECTED_EXCLUDED_ROWS:
        raise ValueError(f"excluded_count_mismatch:{len(excluded)}")
    if len(kept) + len(excluded) != EXPECTED_PARENT_ROWS:
        raise ValueError("kept_plus_excluded_mismatch")
    return {
        "kept": len(kept),
        "excluded": len(excluded),
        "parent_total": EXPECTED_PARENT_ROWS,
        "overlap": 0,
        "pass": True,
    }


def build_v1r2_ident_filtered_split_witness(
    rows: Sequence[Mapping[str, Any]],
    *,
    dataset_sha256: str,
    dataset_path: str,
    code_revision: str,
    exclusion_identities: Sequence[str] | None = None,
) -> dict[str, Any]:
    """V1R2 split witness — parent membership preserved; no new split."""
    if dataset_sha256 != V1R2_DATASET_SHA256_PIN:
        raise ValueError("INPUT_IDENTITY:dataset_mismatch")
    train_rows = [row for row in rows if row.get("split") == "train"]
    val_rows = [row for row in rows if row.get("split") == "validation"]
    train_ids = [str(row["identity"]) for row in train_rows]
    val_ids = [str(row["identity"]) for row in val_rows]
    train_id_sha = identity_list_sha256(train_ids)
    val_id_sha = identity_list_sha256(val_ids)
    train_split_sha = split_lines_sha256(dataset_path, split="train")
    val_split_sha = split_lines_sha256(dataset_path, split="validation")
    verify_v1r2_split_pins(
        train_rows=train_rows,
        validation_rows=val_rows,
        train_split_sha256=train_split_sha,
        validation_split_sha256=val_split_sha,
        train_identity_list_sha256=train_id_sha,
        validation_identity_list_sha256=val_id_sha,
    )
    if exclusion_identities is not None:
        excluded = set(str(x) for x in exclusion_identities)
        resurrected = (set(train_ids) | set(val_ids)) & excluded
        if resurrected:
            raise ValueError(f"EXCLUSION_RESURRECTION:{len(resurrected)}")
    steps = len(
        full_pass_batch_indices(
            EXPECTED_TRAIN_ROWS,
            batch_size=int(TRAIN_HYPERPARAMS["micro_batch_size"]),
            seed=int(TRAIN_HYPERPARAMS["seed"]),
            drop_last=DROP_LAST,
        )
    )
    if steps != EXPECTED_OPTIMIZER_STEPS_PER_EPOCH:
        raise ValueError(
            f"INPUT_IDENTITY:optimizer_steps_per_epoch!={EXPECTED_OPTIMIZER_STEPS_PER_EPOCH}"
        )
    witness = {
        "DATASET_VERSION": DATASET_VERSION,
        "SURFACE_ID": SURFACE_ID,
        "class_balanced_sampler": False,
        "code_revision": code_revision,
        "dataset_sha256": dataset_sha256,
        "drop_last": DROP_LAST,
        "exclusion_resurrection": 0,
        "optimizer_steps_per_epoch": steps,
        "oversampling": False,
        "parent_split_membership_preserved": True,
        "relation_train_eligible": EXPECTED_RELATION_TRAIN_ELIGIBLE,
        "relation_train_masked": EXPECTED_RELATION_TRAIN_MASKED,
        "replacement": False,
        "sampling": "full_pass_deterministic_shuffle",
        "schema": (
            "hyperlex.classification.v5."
            "stage_a_ident_filtered_factorized_split_witness.v1"
        ),
        "shuffle_seed": int(TRAIN_HYPERPARAMS["seed"]),
        "spent_reserve": SPENT_RESERVE,
        "spent_reserve_overlap": SPENT_RESERVE_OVERLAP,
        "spent_reserve_status": SPENT_RESERVE_STATUS,
        "train_dataloader_len": steps,
        "train_identity_list_sha256": train_id_sha,
        "train_rows": EXPECTED_TRAIN_ROWS,
        "train_split_sha256": train_split_sha,
        "train_validation_identity_overlap": 0,
        "undersampling": False,
        "validation_identity_list_sha256": val_id_sha,
        "validation_rows": EXPECTED_VALIDATION_ROWS,
        "validation_split_sha256": val_split_sha,
    }
    witness["V1R2_IDENT_FILTERED_SPLIT_WITNESS_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in witness.items()
                if k != "V1R2_IDENT_FILTERED_SPLIT_WITNESS_SHA256"
            }
        )
    )
    return witness


def verify_v1r2_split_pins(
    *,
    train_rows: Sequence[Mapping[str, Any]],
    validation_rows: Sequence[Mapping[str, Any]],
    train_split_sha256: str,
    validation_split_sha256: str,
    train_identity_list_sha256: str,
    validation_identity_list_sha256: str,
) -> dict[str, Any]:
    if len(train_rows) != EXPECTED_TRAIN_ROWS:
        raise ValueError("train_count_mismatch")
    if len(validation_rows) != EXPECTED_VALIDATION_ROWS:
        raise ValueError("validation_count_mismatch")
    train_ids = [str(r["identity"]) for r in train_rows]
    val_ids = [str(r["identity"]) for r in validation_rows]
    if set(train_ids) & set(val_ids):
        raise ValueError("train_validation_overlap")
    if len(train_ids) + len(val_ids) != EXPECTED_V1R2_ROWS:
        raise ValueError("split_union_mismatch")
    if train_split_sha256 != EXPECTED_TRAIN_SPLIT_SHA256:
        raise ValueError("train_split_sha_mismatch")
    if validation_split_sha256 != EXPECTED_VALIDATION_SPLIT_SHA256:
        raise ValueError("validation_split_sha_mismatch")
    if train_identity_list_sha256 != EXPECTED_TRAIN_IDENTITY_LIST_SHA256:
        raise ValueError("train_identity_sha_mismatch")
    if validation_identity_list_sha256 != EXPECTED_VALIDATION_IDENTITY_LIST_SHA256:
        raise ValueError("validation_identity_sha_mismatch")
    if identity_list_sha256(train_ids) != train_identity_list_sha256:
        raise ValueError("live_train_identity_mismatch")
    if identity_list_sha256(val_ids) != validation_identity_list_sha256:
        raise ValueError("live_val_identity_mismatch")
    return {
        "pass": True,
        "expected": {
            "train_rows": EXPECTED_TRAIN_ROWS,
            "validation_rows": EXPECTED_VALIDATION_ROWS,
            "train_split_sha256": EXPECTED_TRAIN_SPLIT_SHA256,
            "validation_split_sha256": EXPECTED_VALIDATION_SPLIT_SHA256,
            "train_identity_list_sha256": EXPECTED_TRAIN_IDENTITY_LIST_SHA256,
            "validation_identity_list_sha256": (
                EXPECTED_VALIDATION_IDENTITY_LIST_SHA256
            ),
        },
    }


def resolve_ident_filtered_factorized_class_weights(
    train_rows: Sequence[Mapping[str, Any]],
    annotations: Sequence[Mapping[str, Any]],
    *,
    dataset_sha256: str,
    annotation_sha256: str,
    exclusion_manifest_sha256: str,
    train_split_sha256: str,
    train_identity_list_sha256: str,
    code_revision: str,
) -> dict[str, Any]:
    """RESOLVE_STAGE_A_IDENT_FILTERED_FACTORIZED_CLASS_WEIGHTS — train only."""
    if dataset_sha256 != V1R2_DATASET_SHA256_PIN:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:dataset_mismatch")
    if annotation_sha256 != V1R2_ANNOTATION_SHA256_PIN:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:annotation_mismatch")
    if exclusion_manifest_sha256 != V1R2_EXCLUSION_MANIFEST_SHA256_PIN:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:exclusion_mismatch")
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
    uncertain_ids: list[str] = []

    for row in train_rows:
        identity = str(row["identity"])
        ann = ann_index.get(identity)
        if ann is None:
            raise ValueError(
                f"CLASS_WEIGHT_RESOLUTION_INVALID:missing_annotation:{identity}"
            )
        if str(ann["source_gold_label"]) != str(row["evidence_label"]):
            raise ValueError(
                f"CLASS_WEIGHT_RESOLUTION_INVALID:gold_mismatch:{identity}"
            )
        if str(row.get("evidence_label") or "") == "UNCERTAIN":
            uncertain_ids.append(identity)

        resolvable = int(ann["semantic_resolvable"])
        res_label = RESOLVABILITY_LABELS[resolvable]
        _account_row(resolvability_accounts[res_label], row.get("provenance"))

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

    if len(relation_eligible_ids) != EXPECTED_RELATION_TRAIN_ELIGIBLE:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:relation_eligible_count")
    if len(relation_masked_ids) != EXPECTED_RELATION_TRAIN_MASKED:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:masked_count")
    if sorted(relation_masked_ids) != sorted(uncertain_ids):
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:masked_vs_uncertain")

    elig_sha = identity_list_sha256(relation_eligible_ids)
    mask_sha = identity_list_sha256(relation_masked_ids)
    if elig_sha != EXPECTED_RELATION_TRAIN_ELIGIBLE_ID_SHA256:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:eligible_id_sha")
    if mask_sha != EXPECTED_RELATION_TRAIN_MASKED_ID_SHA256:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:masked_id_sha")

    relation_final = _finalize_binary_accounts(
        relation_accounts, labels=RELATION_LABELS
    )
    resolvability_final = _finalize_binary_accounts(
        resolvability_accounts, labels=RESOLVABILITY_LABELS
    )
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
    # Pin expected literals (fail closed on drift).
    for label, expected in LITERAL_RELATION_WEIGHTS.items():
        if abs(literal_weights["relation"][label] - expected) > 1e-12:
            raise ValueError(f"relation_weight_drift:{label}")
    for label, expected in LITERAL_RESOLVABILITY_WEIGHTS.items():
        if abs(literal_weights["resolvability"][label] - expected) > 1e-12:
            raise ValueError(f"resolvability_weight_drift:{label}")

    payload = {
        "CLASS_WEIGHT_RESOLUTION_RULE": CLASS_WEIGHT_RESOLUTION_RULE,
        "OBJECTIVE_ID": OBJECTIVE_ID,
        "SURFACE_ID": SURFACE_ID,
        "DATASET_VERSION": DATASET_VERSION,
        "annotation_sha256": annotation_sha256,
        "clip_policy": {
            "max": CLASS_WEIGHT_POLICY["clip_max"],
            "min": CLASS_WEIGHT_POLICY["clip_min"],
            "renormalize_after_clip": False,
        },
        "code_revision": code_revision,
        "dataset_sha256": dataset_sha256,
        "exclusion_manifest_sha256": exclusion_manifest_sha256,
        "literal_weights": literal_weights,
        "parent_dataset_sha256": PARENT_DATASET_SHA256,
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
                "n_uncertain": len(uncertain_ids),
            },
            "eligible_identity_list_sha256": elig_sha,
            "masked_identity_list_sha256": mask_sha,
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
        "reused_prior_factorized_weights": False,
        "schema": SCHEMA_CLASS_WEIGHTS,
        "surface_receipt_sha256": FILTER_RECEIPT_SHA256_PIN,
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


def ident_filtered_resolved_config(
    *,
    dataset_sha256: str,
    annotation_sha256: str,
    exclusion_manifest_sha256: str,
    class_weight_artifact: Mapping[str, Any],
    code_revision: str,
    tokenizer_identity: str,
    train_split_sha256: str,
    validation_split_sha256: str,
    train_identity_list_sha256: str,
    validation_identity_list_sha256: str,
    surface_receipt_sha256: str,
    objective_receipt_sha256: str,
) -> dict[str, Any]:
    if dataset_sha256 != V1R2_DATASET_SHA256_PIN:
        raise ValueError("resolved_config:dataset_mismatch")
    if annotation_sha256 != V1R2_ANNOTATION_SHA256_PIN:
        raise ValueError("resolved_config:annotation_mismatch")
    if exclusion_manifest_sha256 != V1R2_EXCLUSION_MANIFEST_SHA256_PIN:
        raise ValueError("resolved_config:exclusion_mismatch")
    if surface_receipt_sha256 != FILTER_RECEIPT_SHA256_PIN:
        raise ValueError("resolved_config:surface_receipt_mismatch")
    if objective_receipt_sha256 != OBJECTIVE_RECEIPT_SHA256_PIN:
        raise ValueError("resolved_config:objective_receipt_mismatch")

    config = {
        "OBJECTIVE_ID": OBJECTIVE_ID,
        "OBJECTIVE_RULE": OBJECTIVE_RULE,
        "OBJECTIVE_RECEIPT_SHA256": objective_receipt_sha256,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "SCIENTIFIC_QUESTION": SCIENTIFIC_QUESTION,
        "SURFACE_ID": SURFACE_ID,
        "DATASET_VERSION": DATASET_VERSION,
        "FILTER_RULE": FILTER_RULE,
        "FILTER_ID": FILTER_ID,
        "CONTRACT_RECEIPT_SHA256": CONTRACT_RECEIPT_SHA256_PIN,
        "PARENT_DATASET_SHA256": PARENT_DATASET_SHA256,
        "PARENT_DECOMPOSITION": PARENT_DECOMPOSITION,
        "POSSIBLE_EVIDENCE_STATUS": POSSIBLE_EVIDENCE_STATUS,
        "DOMAIN_IRRELEVANT_GENERALIZATION": DOMAIN_IRRELEVANT_GENERALIZATION,
        "SHORT_ATOM_POSITIVE_GENERALIZATION": SHORT_ATOM_POSITIVE_GENERALIZATION,
        "SEMANTIC_DECOMPOSITION_RECEIPT_SHA256": SEMANTIC_DECOMPOSITION_RECEIPT_SHA256,
        "MODEL_INPUT": ["text"],
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
        "exclusion_manifest_sha256": exclusion_manifest_sha256,
        "expected_optimizer_steps_per_epoch": EXPECTED_OPTIMIZER_STEPS_PER_EPOCH,
        "expected_train_rows": EXPECTED_TRAIN_ROWS,
        "expected_validation_rows": EXPECTED_VALIDATION_ROWS,
        "explicit_limitations": EXPLICIT_LIMITATIONS,
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
            "metadata_auxiliary_head": False,
        },
        "identifiability_diagnostic_contract": IDENTIFIABILITY_DIAGNOSTIC_CONTRACT,
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
        "no_input_expansion": True,
        "optimizer": TRAIN_HYPERPARAMS["optimizer"],
        "padding": TRAIN_HYPERPARAMS["padding"],
        "pooling": TRAIN_HYPERPARAMS["pooling"],
        "provenance_weights": dict(PROVENANCE_LOSS_MULTIPLIERS),
        "relation_class_weights_literal": dict(
            class_weight_artifact["literal_weights"]["relation"]
        ),
        "relation_eligible_identity_list_sha256": class_weight_artifact["relation"][
            "eligible_identity_list_sha256"
        ],
        "relation_eligible_total": EXPECTED_RELATION_ELIGIBLE_TOTAL,
        "relation_masked_identity_list_sha256": class_weight_artifact["relation"][
            "masked_identity_list_sha256"
        ],
        "relation_masked_total": EXPECTED_RELATION_MASKED_TOTAL,
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


def ident_filtered_authorization_contract(
    *,
    dataset_sha256: str,
    annotation_sha256: str,
    exclusion_manifest_sha256: str,
    training_config_sha256: str,
    class_weight_artifact_sha256: str,
    code_revision: str,
    surface_receipt_sha256: str,
    objective_receipt_sha256: str,
) -> dict[str, Any]:
    auth = {
        "AUTHORIZE_RULE": AUTHORIZE_RULE,
        "ANNOTATION_SHA256": annotation_sha256,
        "CLASS_WEIGHT_ARTIFACT_SHA256": class_weight_artifact_sha256,
        "CONTRACT_RECEIPT_SHA256": CONTRACT_RECEIPT_SHA256_PIN,
        "CURRENT_STAGE_A_BEST": PARENT_STAGE_A_BEST_SHA,
        "CURRENT_STAGE_A_BEST_MUTATED": False,
        "DATASET_SHA256": dataset_sha256,
        "DATASET_VERSION": DATASET_VERSION,
        "DOMAIN_IRRELEVANT_GENERALIZATION": DOMAIN_IRRELEVANT_GENERALIZATION,
        "EXCLUSION_MANIFEST_SHA256": exclusion_manifest_sha256,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "EXPLICIT_LIMITATIONS": EXPLICIT_LIMITATIONS,
        "FILTER_RECEIPT_SHA256": FILTER_RECEIPT_SHA256_PIN,
        "MODEL_INPUT": ["text"],
        "MODEL_WIDE_BEST": BEST_SHA,
        "MODEL_WIDE_BEST_MUTATED": False,
        "NEXT_ACTION": TRAIN_ONCE_ACTION,
        "OBJECTIVE_ID": OBJECTIVE_ID,
        "OBJECTIVE_RECEIPT_SHA256": objective_receipt_sha256,
        "PARENT_DATASET_SHA256": PARENT_DATASET_SHA256,
        "PARENT_DECOMPOSITION": PARENT_DECOMPOSITION,
        "SCIENTIFIC_QUESTION": SCIENTIFIC_QUESTION,
        "SCIENTIFIC_RESULT": "NOT_COMPUTABLE",
        "SHORT_ATOM_POSITIVE_GENERALIZATION": SHORT_ATOM_POSITIVE_GENERALIZATION,
        "SPENT_RESERVE": SPENT_RESERVE,
        "SPENT_RESERVE_OVERLAP": SPENT_RESERVE_OVERLAP,
        "SPENT_RESERVE_STATUS": SPENT_RESERVE_STATUS,
        "STAGE_B_MUTATED": False,
        "SURFACE_ID": SURFACE_ID,
        "SURFACE_RECEIPT_SHA256": surface_receipt_sha256,
        "TRAIN_AUTHORIZED": True,
        "TRAINING_CONFIG_SHA256": training_config_sha256,
        "TRAINING_RUN_LIMIT": 1,
        "TRAINING_STATUS": "AUTHORIZED_NOT_STARTED",
        "V1R1_MUTATED": False,
        "V1R2_MUTATED": False,
        "code_revision": code_revision,
        "initialization_policy": INITIALIZATION_POLICY,
        "schema": SCHEMA_AUTH,
        "spent_reserve_access_for_train_val_select_threshold_diag": False,
    }
    return auth
