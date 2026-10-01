"""HYPERLEX_V5_STAGE_A_FACTORIZED_RELATION_OBJECTIVE_V1 — frozen spec.

Relation-only Stage-A objective: supervise evidence_relation_present and
semantic_resolvable; derive final three-way Stage-A decisions deterministically.

Spec / annotation derivation only. Does not train, create V1R2, human-relabel,
alter Stage B, score spent reserve, or move BEST.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from .classification_v5_stage_a import (
    ACCEPTANCE_GATES,
    BEST_SHA,
    EVIDENCE_LABELS,
    PROVENANCE_LOSS_MULTIPLIERS,
    TRAIN_HYPERPARAMS,
    canonical_json,
    sha256_text,
)
from .classification_v5_stage_a_semantic_decomposition import (
    DECOMPOSITION_RULE,
    DIAGNOSIS_RECEIPT_SHA256,
    FROZEN_V1R1_SUBTYPE_COUNTS,
    PRIMARY_DIAGNOSIS,
)
from .classification_v5_stage_a_two_stage_generalization import (
    AUTHORIZED_DATASET_SHA,
    AUTHORIZED_READINESS_SHA,
    AUTHORIZED_SURFACE_RECEIPT_SHA,
    PARENT_STAGE_A_BEST_SHA,
    SPENT_RESERVE,
    SPENT_RESERVE_OVERLAP,
    SPENT_RESERVE_STATUS,
)

OBJECTIVE_ID = "HYPERLEX_V5_STAGE_A_FACTORIZED_RELATION_OBJECTIVE_V1"
OBJECTIVE_RULE = "SPEC_STAGE_A_FACTORIZED_OBJECTIVE"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-001"
PARENT_EXPERIMENT_ID = "HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-GENERALIZATION-001"
PARENT_DECOMPOSITION = "RELATION_ONLY_DECOMPOSITION"
SEMANTIC_DECOMPOSITION_RECEIPT_SHA256 = (
    "93202898969e7102016db97abfa2bdf2fd7921dbba1ade90310e4b7693f5d032"
)

# Sealed from V1R1 EVIDENCE_SURFACE @ AUTHORIZED_DATASET_SHA (3585 rows).
FACTORIZED_ANNOTATION_SHA256_PIN = (
    "4ac884504e4b2fe27e0e5de159847a158c43e2c0d75832ddc5b5c657279778b6"
)
OBJECTIVE_RECEIPT_SHA256_PIN = (
    "45746d706d819da41eb56e788f13f4a873f8dc136c0057c9fa238a53b5bacfdc"
)

FACTORIZED_OBJECTIVE_SPEC = "FROZEN"
TRAIN_AUTHORIZED = False
ARCHITECTURE_CHANGE_REQUIRED = False

DERIVATION_RULE_ID = "HYPERLEX_V5_STAGE_A_FACTORIZED_ANNOTATION_DERIVE_V1"
DERIVATION_RULE_VERSION = "v1"
ANNOTATION_SCHEMA = "hyperlex.stage_a.factorized_annotation.v1"
SCHEMA_OBJECTIVE = "hyperlex.classification.v5.stage_a_factorized_objective.v1"
SCHEMA_FORWARD = "hyperlex.classification.v5.stage_a_factorized_forward.v1"
SCHEMA_MANIFEST = "hyperlex.classification.v5.stage_a_factorized_annotation_manifest.v1"

MASKED = "MASKED"
UNKNOWN = "UNKNOWN"

RELATION_LABELS = ("NO_EVIDENCE_RELATION", "EVIDENCE_RELATION_PRESENT")
RELATION_INDEX = {label: index for index, label in enumerate(RELATION_LABELS)}
RESOLVABILITY_LABELS = ("UNRESOLVABLE", "RESOLVABLE")
RESOLVABILITY_INDEX = {
    label: index for index, label in enumerate(RESOLVABILITY_LABELS)
}

CANONICAL_LABELS = EVIDENCE_LABELS
POSSIBLE_EVIDENCE_STATUS = "DEPRECATED_AS_STAGE_A_TRAINING_TARGET"

LAMBDA_RESOLVABILITY = 1.0
LOSS_NAME = "weighted_cross_entropy"
FOCAL_FORBIDDEN = True
LAST_TRAINABLE_ENCODER_LAYERS = int(TRAIN_HYPERPARAMS["last_trainable"])
POOLING = str(TRAIN_HYPERPARAMS["pooling"])
HEAD_INIT = str(TRAIN_HYPERPARAMS["head_init"])

RELATION_THRESHOLDS = [round(0.50 + 0.05 * i, 2) for i in range(10)]
RESOLVABILITY_THRESHOLDS = [round(0.50 + 0.05 * i, 2) for i in range(10)]

EXPECTED_ROW_COUNT = 3585
EXPECTED_SUBTYPE_COUNTS = dict(FROZEN_V1R1_SUBTYPE_COUNTS)

# Subtype → derived primitives. FAIL_CLOSED for anything else.
SUPPORTED_DERIVATIONS: dict[str, dict[str, Any]] = {
    "POSITIVE_EVIDENCE": {
        "evidence_relation_present": 1,
        "semantic_resolvable": 1,
        "domain_relevant_derived": 1,
        "source_gold_label": "EVIDENCE_PRESENT",
    },
    "ORDINARY_DOMAIN_NONE": {
        "evidence_relation_present": 0,
        "semantic_resolvable": 1,
        "domain_relevant_derived": 1,
        "source_gold_label": "NO_EVIDENCE",
    },
    "LEXICAL_LOOKALIKE_NONE": {
        "evidence_relation_present": 0,
        "semantic_resolvable": 1,
        "domain_relevant_derived": 1,
        "source_gold_label": "NO_EVIDENCE",
    },
    "SHORT_ATOM_NONE": {
        "evidence_relation_present": 0,
        "semantic_resolvable": 1,
        "domain_relevant_derived": 1,
        "source_gold_label": "NO_EVIDENCE",
    },
    "NEAR_DOMAIN_NONE": {
        "evidence_relation_present": 0,
        "semantic_resolvable": 1,
        "domain_relevant_derived": 1,
        "source_gold_label": "NO_EVIDENCE",
    },
    "HARD_NONE": {
        "evidence_relation_present": 0,
        "semantic_resolvable": 1,
        "domain_relevant_derived": 1,
        "source_gold_label": "NO_EVIDENCE",
    },
    "AMBIGUOUS_EVIDENCE": {
        "evidence_relation_present": MASKED,
        "semantic_resolvable": 0,
        "domain_relevant_derived": UNKNOWN,
        "source_gold_label": "UNCERTAIN",
    },
}

RELATION_CRITICAL_RULE = {
    "RELATION_HEAD_POSITIVE_means": (
        "asserted/instantiated evidence relation"
    ),
    "NOT": [
        "domain_relevance",
        "family_cue",
        "lexeme_presence",
        "source_membership",
        "dictionary_headword_presence",
    ],
    "short_atom": (
        "relation-positive only when existing gold supports an actual "
        "asserted relation (POSITIVE_EVIDENCE)"
    ),
}

DOMAIN_IRRELEVANT_GENERALIZATION = "NOT_ESTABLISHED"

NEXT_ACTION = "AUTHORIZE_STAGE_A_FACTORIZED_RELATION_TRAIN"


class UnsupportedSubtypeError(ValueError):
    """Raised when a subtype has no sealed derivation (FAIL_CLOSED)."""


def derivation_input_hash(
    *,
    identity: str,
    source_gold_label: str,
    source_subtype: str,
) -> str:
    return sha256_text(
        canonical_json(
            {
                "identity": identity,
                "source_gold_label": source_gold_label,
                "source_subtype": source_subtype,
                "derivation_rule_id": DERIVATION_RULE_ID,
                "derivation_rule_version": DERIVATION_RULE_VERSION,
                "source_dataset_sha256": AUTHORIZED_DATASET_SHA,
            }
        )
    )


def annotation_row_sha256(row: Mapping[str, Any]) -> str:
    payload = {k: v for k, v in row.items() if k != "annotation_sha256"}
    return sha256_text(canonical_json(payload))


def derive_factorized_annotation(row: Mapping[str, Any]) -> dict[str, Any]:
    """Derive one sidecar annotation from sealed gold/subtype fields only."""
    identity = str(row["identity"])
    subtype = str(row.get("evidence_subtype") or "")
    gold = str(row.get("evidence_label") or "")
    mapping = SUPPORTED_DERIVATIONS.get(subtype)
    if mapping is None:
        raise UnsupportedSubtypeError(
            f"UNSUPPORTED_SUBTYPE_FAIL_CLOSED:{subtype}:{identity}"
        )
    expected_gold = mapping["source_gold_label"]
    if gold != expected_gold:
        raise ValueError(
            f"GOLD_SUBTYPE_MISMATCH:{identity}:{subtype}:{gold}!={expected_gold}"
        )
    # Guard: no model-derived fields may feed derivation.
    forbidden = (
        "p_possible",
        "p_confirmed",
        "gate1_logits",
        "gate2_logits",
        "model_score",
        "embedding",
    )
    for key in forbidden:
        if key in row and row.get(key) is not None:
            raise ValueError(f"MODEL_DERIVED_FIELD_FORBIDDEN:{key}:{identity}")

    input_hash = derivation_input_hash(
        identity=identity,
        source_gold_label=gold,
        source_subtype=subtype,
    )
    annotation = {
        "identity": identity,
        "source_gold_label": gold,
        "source_subtype": subtype,
        "evidence_relation_present": mapping["evidence_relation_present"],
        "semantic_resolvable": mapping["semantic_resolvable"],
        "domain_relevant_derived": mapping["domain_relevant_derived"],
        "derivation_rule_id": DERIVATION_RULE_ID,
        "derivation_rule_version": DERIVATION_RULE_VERSION,
        "derivation_input_hash": input_hash,
        "schema": ANNOTATION_SCHEMA,
    }
    annotation["annotation_sha256"] = annotation_row_sha256(annotation)
    return annotation


def decide_stage_a(
    *,
    p_evidence_relation_present: float,
    p_resolvable: float,
    relation_threshold: float,
    resolvability_threshold: float,
) -> str:
    """Deterministic final Stage-A decision from head probabilities."""
    if float(p_resolvable) < float(resolvability_threshold):
        return "UNCERTAIN"
    if float(p_evidence_relation_present) >= float(relation_threshold):
        return "EVIDENCE_PRESENT"
    return "NO_EVIDENCE"


def relation_loss_eligible(annotation: Mapping[str, Any]) -> bool:
    return int(annotation["semantic_resolvable"]) == 1 and annotation[
        "evidence_relation_present"
    ] != MASKED


def resolvability_loss_eligible(annotation: Mapping[str, Any]) -> bool:
    return annotation.get("semantic_resolvable") in (0, 1)


def architecture_contract() -> dict[str, Any]:
    return {
        "ARCHITECTURE_CHANGE_REQUIRED": ARCHITECTURE_CHANGE_REQUIRED,
        "encoder": "ModernBERT-base",
        "forbidden_additions": [
            "mlp_head",
            "attention_block",
            "retrieval",
            "prototype_scoring",
            "domain_head",
            "family_head",
        ],
        "head_init": HEAD_INIT,
        "last_trainable_encoder_layers": LAST_TRAINABLE_ENCODER_LAYERS,
        "pooling": POOLING,
        "relation_head": "linear_hidden_to_2_logits",
        "resolvability_head": "linear_hidden_to_2_logits",
        "shared_encoder": True,
        "trainable": {
            "last_trainable_encoder_layers": LAST_TRAINABLE_ENCODER_LAYERS,
            "relation_head": True,
            "resolvability_head": True,
            "mutate_best": False,
        },
        "note": (
            "Encoder topology and two-head form unchanged; only head "
            "semantics/objective change from Gate1/Gate2."
        ),
    }


def loss_contract() -> dict[str, Any]:
    return {
        "L_total": "L_relation + lambda_resolvability * L_resolvability",
        "focal_forbidden": FOCAL_FORBIDDEN,
        "lambda_resolvability": LAMBDA_RESOLVABILITY,
        "lambda_optimized_in_this_pass": False,
        "name": "factorized_relation_weighted_ce",
        "provenance_multipliers": dict(PROVENANCE_LOSS_MULTIPLIERS),
        "relation": {
            "loss": LOSS_NAME,
            "scope": "semantic_resolvable == 1",
            "targets": {
                "NO_EVIDENCE_RELATION": 0,
                "EVIDENCE_RELATION_PRESENT": 1,
            },
            "masked": "AMBIGUOUS_EVIDENCE / semantic_resolvable == 0",
        },
        "resolvability": {
            "loss": LOSS_NAME,
            "scope": "all_valid_stage_a_rows",
            "targets": {"UNRESOLVABLE": 0, "RESOLVABLE": 1},
        },
        "class_weights": {
            "resolve_separately_per_head": True,
            "source_split": "train_only",
            "reuse_previous_gate1_gate2_weights": False,
        },
    }


def threshold_contract() -> dict[str, Any]:
    return {
        "grids": {
            "relation_threshold": list(RELATION_THRESHOLDS),
            "resolvability_threshold": list(RESOLVABILITY_THRESHOLDS),
        },
        "n_pairs": 100,
        "thresholds_chosen_in_this_pass": False,
    }


def acceptance_contract() -> dict[str, Any]:
    return {
        "hard_gates": {
            "false_evidence_entry_rate_on_none_max": ACCEPTANCE_GATES[
                "false_evidence_entry_rate_on_none_max"
            ],
            "EVIDENCE_PRESENT_recall_min": ACCEPTANCE_GATES[
                "EVIDENCE_PRESENT_recall_min"
            ],
            "NO_EVIDENCE_recall_min": ACCEPTANCE_GATES["NO_EVIDENCE_recall_min"],
        },
        "diagnostic_only": [
            "UNCERTAIN_recall",
            "relation_head_macro_F1",
            "resolvability_head_macro_F1",
            "relation_false_positive_rate_on_SHORT_ATOM_NONE",
            "relation_recall_on_SHORT_ATOM_PRESENT",
        ],
        "new_hard_promotion_gates_in_this_spec": False,
    }


def short_atom_diagnostic_contract() -> dict[str, Any]:
    return {
        "cells": [
            "SHORT_ATOM/NO_EVIDENCE",
            "SHORT_ATOM/EVIDENCE_PRESENT",
        ],
        "scientific_test": (
            "Does direct relation supervision improve SHORT_ATOM NONE "
            "rejection without destroying SHORT_ATOM PRESENT recall?"
        ),
        "replaces": "old Gate1 NO_EVIDENCE vs POSSIBLE_EVIDENCE proxy on SHORT_ATOM",
    }


def stage_b_compatibility() -> dict[str, Any]:
    return {
        "entry_contract_unchanged": True,
        "EVIDENCE_PRESENT": "Stage B permitted",
        "NO_EVIDENCE": "stop",
        "UNCERTAIN": "abstain",
        "stage_b_code_index_floors_change_justified": False,
    }


def old_vs_new_objective() -> dict[str, Any]:
    return {
        "OLD": {
            "Gate1": "NO_EVIDENCE vs POSSIBLE_EVIDENCE",
            "Gate2": "CONFIRMED_PRESENT vs UNCERTAIN",
        },
        "NEW": {
            "Head_A": "EVIDENCE_RELATION_PRESENT vs NO_EVIDENCE_RELATION",
            "Head_B": "RESOLVABLE vs UNRESOLVABLE",
        },
        "POSSIBLE_EVIDENCE": POSSIBLE_EVIDENCE_STATUS,
        "historical_artifacts_retained": True,
    }


def build_annotations(
    rows: Sequence[Mapping[str, Any]],
    *,
    source_dataset_sha256: str,
) -> dict[str, Any]:
    """Materialize sidecar annotations + integrity witnesses from V1R1 rows."""
    if source_dataset_sha256 != AUTHORIZED_DATASET_SHA:
        raise ValueError(
            f"SOURCE_DATASET_SHA_MISMATCH:{source_dataset_sha256}"
        )
    if len(rows) != EXPECTED_ROW_COUNT:
        raise ValueError(f"ROW_COUNT_MISMATCH:{len(rows)}!={EXPECTED_ROW_COUNT}")

    annotations: list[dict[str, Any]] = []
    seen: set[str] = set()
    subtype_counts: Counter[str] = Counter()
    unsupported = 0

    for row in rows:
        identity = str(row["identity"])
        if identity in seen:
            raise ValueError(f"DUPLICATE_IDENTITY:{identity}")
        seen.add(identity)
        subtype = str(row.get("evidence_subtype") or "")
        subtype_counts[subtype] += 1
        try:
            annotations.append(derive_factorized_annotation(row))
        except UnsupportedSubtypeError:
            unsupported += 1
            raise

    if unsupported != 0:
        raise ValueError(f"UNSUPPORTED_SUBTYPE_DERIVATIONS:{unsupported}")

    for subtype, expected in EXPECTED_SUBTYPE_COUNTS.items():
        actual = int(subtype_counts.get(subtype, 0))
        if actual != int(expected):
            raise ValueError(
                f"SUBTYPE_COUNT_MISMATCH:{subtype}:{actual}!={expected}"
            )
    extras = set(subtype_counts) - set(EXPECTED_SUBTYPE_COUNTS)
    # Allow only known keys; GENERIC_NONE expected 0 and may be absent.
    for subtype in extras:
        if subtype not in SUPPORTED_DERIVATIONS:
            raise ValueError(f"UNEXPECTED_SUBTYPE:{subtype}")

    relation_pos = sum(
        1 for a in annotations if a["evidence_relation_present"] == 1
    )
    relation_neg = sum(
        1 for a in annotations if a["evidence_relation_present"] == 0
    )
    relation_masked = sum(
        1 for a in annotations if a["evidence_relation_present"] == MASKED
    )
    resolvable_pos = sum(1 for a in annotations if a["semantic_resolvable"] == 1)
    resolvable_neg = sum(1 for a in annotations if a["semantic_resolvable"] == 0)
    relation_eligible = sum(1 for a in annotations if relation_loss_eligible(a))
    resolvability_eligible = sum(
        1 for a in annotations if resolvability_loss_eligible(a)
    )

    if relation_pos != EXPECTED_SUBTYPE_COUNTS["POSITIVE_EVIDENCE"]:
        raise ValueError("RELATION_POS_COUNT_MISMATCH")
    if relation_neg != sum(
        EXPECTED_SUBTYPE_COUNTS[s]
        for s in (
            "ORDINARY_DOMAIN_NONE",
            "LEXICAL_LOOKALIKE_NONE",
            "SHORT_ATOM_NONE",
            "NEAR_DOMAIN_NONE",
            "HARD_NONE",
        )
    ):
        raise ValueError("RELATION_NEG_COUNT_MISMATCH")
    if relation_masked != EXPECTED_SUBTYPE_COUNTS["AMBIGUOUS_EVIDENCE"]:
        raise ValueError("RELATION_MASKED_COUNT_MISMATCH")
    if resolvable_pos != relation_pos + relation_neg:
        raise ValueError("RESOLVABLE_POS_COUNT_MISMATCH")
    if resolvable_neg != relation_masked:
        raise ValueError("RESOLVABLE_NEG_COUNT_MISMATCH")
    if relation_eligible != relation_pos + relation_neg:
        raise ValueError("RELATION_ELIGIBLE_COUNT_MISMATCH")
    if resolvability_eligible != len(annotations):
        raise ValueError("RESOLVABILITY_ELIGIBLE_COUNT_MISMATCH")

    # Canonical jsonl order: sorted by identity for stable artifact hash.
    annotations_sorted = sorted(annotations, key=lambda a: a["identity"])
    jsonl_body = "".join(
        canonical_json(a) + "\n" for a in annotations_sorted
    )
    factorized_annotation_sha256 = sha256_text(jsonl_body)

    counts = {
        "n_rows": len(annotations_sorted),
        "relation_positive": relation_pos,
        "relation_negative": relation_neg,
        "relation_masked": relation_masked,
        "resolvable_positive": resolvable_pos,
        "resolvable_negative": resolvable_neg,
        "relation_loss_eligible": relation_eligible,
        "resolvability_loss_eligible": resolvability_eligible,
        "by_subtype": dict(subtype_counts),
        "domain_relevant_derived": {
            "1": sum(1 for a in annotations if a["domain_relevant_derived"] == 1),
            "0": sum(1 for a in annotations if a["domain_relevant_derived"] == 0),
            "UNKNOWN": sum(
                1 for a in annotations if a["domain_relevant_derived"] == UNKNOWN
            ),
        },
        "duplicate_identities": 0,
        "unsupported_subtype_derivations": 0,
    }

    derivation_witness = {
        "schema": "hyperlex.classification.v5.stage_a_factorized_derivation_witness.v1",
        "source_dataset_sha256": source_dataset_sha256,
        "row_count": len(annotations_sorted),
        "duplicate_identities": 0,
        "unsupported_subtype_derivations": 0,
        "derivation_rule_id": DERIVATION_RULE_ID,
        "derivation_rule_version": DERIVATION_RULE_VERSION,
        "parent_decomposition": PARENT_DECOMPOSITION,
        "semantic_decomposition_receipt_sha256": SEMANTIC_DECOMPOSITION_RECEIPT_SHA256,
        "counts": counts,
        "identity_list_sha256": sha256_text(
            "\n".join(a["identity"] for a in annotations_sorted) + "\n"
        ),
        "FACTORIZED_ANNOTATION_SHA256": factorized_annotation_sha256,
        "model_derived_fields_used": False,
        "human_relabel": False,
        "source_rows_mutated": False,
    }
    derivation_witness["witness_sha256"] = sha256_text(
        canonical_json(
            {k: v for k, v in derivation_witness.items() if k != "witness_sha256"}
        )
    )

    manifest = {
        "schema": SCHEMA_MANIFEST,
        "OBJECTIVE_ID": OBJECTIVE_ID,
        "ANNOTATION_SCHEMA": ANNOTATION_SCHEMA,
        "source_dataset_sha256": source_dataset_sha256,
        "source_readiness_sha256": AUTHORIZED_READINESS_SHA,
        "source_surface_receipt_sha256": AUTHORIZED_SURFACE_RECEIPT_SHA,
        "FACTORIZED_ANNOTATION_SHA256": factorized_annotation_sha256,
        "derivation_witness_sha256": derivation_witness["witness_sha256"],
        "n_rows": len(annotations_sorted),
        "counts": counts,
        "TRAIN_AUTHORIZED": TRAIN_AUTHORIZED,
        "ANNOTATION_DERIVATION": "SEALED",
    }
    manifest["manifest_sha256"] = sha256_text(
        canonical_json({k: v for k, v in manifest.items() if k != "manifest_sha256"})
    )

    return {
        "annotations": annotations_sorted,
        "jsonl_body": jsonl_body,
        "counts": counts,
        "derivation_witness": derivation_witness,
        "manifest": manifest,
        "FACTORIZED_ANNOTATION_SHA256": factorized_annotation_sha256,
    }


def assemble_objective_receipt(
    *,
    annotation_bundle: Mapping[str, Any],
    enforce_pins: bool = True,
) -> dict[str, Any]:
    receipt = {
        "ANNOTATION_DERIVATION": "SEALED",
        "ARCHITECTURE_CHANGE_REQUIRED": ARCHITECTURE_CHANGE_REQUIRED,
        "DOMAIN_IRRELEVANT_GENERALIZATION": DOMAIN_IRRELEVANT_GENERALIZATION,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "FACTORIZED_ANNOTATION_SHA256": annotation_bundle[
            "FACTORIZED_ANNOTATION_SHA256"
        ],
        "FACTORIZED_ANNOTATION_SHA256_PIN": FACTORIZED_ANNOTATION_SHA256_PIN,
        "FACTORIZED_OBJECTIVE_SPEC": FACTORIZED_OBJECTIVE_SPEC,
        "MODEL_WIDE_BEST": BEST_SHA,
        "MODEL_WIDE_BEST_MUTATED": False,
        "NEXT_ACTION": NEXT_ACTION,
        "NEXT_ACTION_AUTHORIZED": False,
        "OBJECTIVE_ID": OBJECTIVE_ID,
        "OBJECTIVE_RULE": OBJECTIVE_RULE,
        "PARENT_DECOMPOSITION": PARENT_DECOMPOSITION,
        "PARENT_EXPERIMENT_ID": PARENT_EXPERIMENT_ID,
        "PARENT_STAGE_A_BEST": PARENT_STAGE_A_BEST_SHA,
        "POSSIBLE_EVIDENCE_STATUS": POSSIBLE_EVIDENCE_STATUS,
        "PRIMARY_DIAGNOSIS": PRIMARY_DIAGNOSIS,
        "SEMANTIC_DECOMPOSITION_RECEIPT_SHA256": SEMANTIC_DECOMPOSITION_RECEIPT_SHA256,
        "SEMANTIC_DECOMPOSITION_RULE": DECOMPOSITION_RULE,
        "DIAGNOSIS_RECEIPT_SHA256": DIAGNOSIS_RECEIPT_SHA256,
        "SPENT_RESERVE": SPENT_RESERVE,
        "SPENT_RESERVE_OVERLAP": SPENT_RESERVE_OVERLAP,
        "SPENT_RESERVE_STATUS": SPENT_RESERVE_STATUS,
        "STAGE_A_BEST": PARENT_STAGE_A_BEST_SHA,
        "STAGE_A_BEST_MUTATED": False,
        "STAGE_B_MUTATED": False,
        "TRAIN": False,
        "TRAIN_AUTHORIZED": TRAIN_AUTHORIZED,
        "V1R1_DATASET_SHA256": AUTHORIZED_DATASET_SHA,
        "V1R1_MUTATED": False,
        "V1R1_READINESS_SHA256": AUTHORIZED_READINESS_SHA,
        "V1R1_SURFACE_RECEIPT_SHA256": AUTHORIZED_SURFACE_RECEIPT_SHA,
        "V1R2_CREATED": False,
        "acceptance": acceptance_contract(),
        "architecture": architecture_contract(),
        "canonical_decision": {
            "logic": [
                "if P(RESOLVABLE) < resolvability_threshold: UNCERTAIN",
                "elif P(EVIDENCE_RELATION_PRESENT) >= relation_threshold: EVIDENCE_PRESENT",
                "else: NO_EVIDENCE",
            ],
            "outputs": list(CANONICAL_LABELS),
            "domain_classifier_required": False,
        },
        "counts": annotation_bundle["counts"],
        "derivation_witness_sha256": annotation_bundle["derivation_witness"][
            "witness_sha256"
        ],
        "loss": loss_contract(),
        "manifest_sha256": annotation_bundle["manifest"]["manifest_sha256"],
        "old_vs_new": old_vs_new_objective(),
        "relation_critical_rule": RELATION_CRITICAL_RULE,
        "schema": SCHEMA_OBJECTIVE,
        "short_atom_diagnostic": short_atom_diagnostic_contract(),
        "stage_b_compatibility": stage_b_compatibility(),
        "thresholds": threshold_contract(),
        "heads": {
            "relation": {
                "labels": list(RELATION_LABELS),
                "index": dict(RELATION_INDEX),
                "predicts": "asserted/instantiated evidence relation",
                "must_not_predict": "domain_relevance",
            },
            "resolvability": {
                "labels": list(RESOLVABILITY_LABELS),
                "index": dict(RESOLVABILITY_INDEX),
                "predicts": "semantic resolvability of evidence judgment",
                "must_not_represent": "model_confidence",
            },
            "domain_relevance_head": False,
        },
    }
    receipt["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    )
    if enforce_pins:
        if (
            annotation_bundle["FACTORIZED_ANNOTATION_SHA256"]
            != FACTORIZED_ANNOTATION_SHA256_PIN
        ):
            raise ValueError(
                "FACTORIZED_ANNOTATION_SHA_PIN_MISMATCH:"
                f"{annotation_bundle['FACTORIZED_ANNOTATION_SHA256']}"
            )
        if receipt["receipt_sha256"] != OBJECTIVE_RECEIPT_SHA256_PIN:
            raise ValueError(
                "OBJECTIVE_RECEIPT_SHA_PIN_MISMATCH:"
                f"{receipt['receipt_sha256']}"
            )
    return receipt
