"""REASSESS_V6_FUNCTION_TASK_SIGNAL — contracts.

Read-only diagnostic: is FUNCTION learnable from text-only input at useful
reliability, or is ~0.30 macro-F1 a task-signal ceiling? No new heads,
threshold tunes, ontology changes, or QUAL optimization.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
from .classification_v6_function_diversity_expand import (
    DEV_V3_ID,
    REP_V3_ID,
    TRAIN_V3_ID,
)
from .classification_v6_function_prediction_redesign import (
    BASELINE_REP_V3,
    FORMULATIONS,
    FUNCTION_DEFINITIONS,
)
from .classification_v6_label_migration import FUNCTION_VOCAB
from .classification_v6_operating_pipeline_harden import WITNESS_GATE_THRESHOLD
from .classification_v6_qualification_003_failure_review import (
    EXPECTED_QUAL_RESULT_SHA256,
)
from .classification_v6_qualification_execute_003 import (
    EXPECTED_PACKAGE_SHA256,
    EXPECTED_SEAL_SHA256,
    QUALIFICATION_ID,
)
from .classification_v6_semantic_pipeline_harden import (
    SELECTED_ENCODER_MODEL_ID,
    SELECTED_ENCODER_REVISION,
)

PHASE_RULE = "REASSESS_V6_FUNCTION_TASK_SIGNAL"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-FUNCTION-TASK-SIGNAL-REASSESS-001"
SCHEMA = "hyperlex.classification.v6.function_task_signal_reassess.v1"

PARENT_REDESIGN_OUTCOME = "V6_FUNCTION_PREDICTION_PARTIAL"
PARENT_SELECTED = "INDEPENDENT_BINARY_VERIFIERS"

SIGNAL_CLASSES = (
    "STRONG_TEXT_SIGNAL",
    "WEAK_BUT_LEARNABLE",
    "CONTEXT_SENSITIVE",
    "SEMANTICALLY_OVERLAPPING",
    "INSUFFICIENT_SUPPORT",
)

CEILING_CLASSES = (
    "NO_CLEAR_CEILING",
    "DATA_LIMITED_CEILING",
    "TEXT_SIGNAL_CEILING",
    "ANNOTATION_BOUNDARY_CEILING",
    "MIXED_CEILING",
)

DIAGNOSES = (
    "FUNCTION_TASK_SIGNAL_SUPPORTED",
    "FUNCTION_TASK_SIGNAL_PARTIAL",
    "FUNCTION_TASK_SIGNAL_INSUFFICIENT",
)

NEXT_ACTIONS = (
    "REDESIGN_V6_FUNCTION_OBJECTIVE_AROUND_PRAGMATIC_SIGNAL",
    "SPLIT_V6_FUNCTIONS_BY_SIGNAL_REGIME",
    "REASSESS_V6_FUNCTION_PRODUCT_REQUIREMENT",
    "TARGETED_FUNCTION_SUPPORT_EXPANSION",
)

AXIS_STRUCTURES = (
    "independent_binary_predicates",
    "soft_overlapping_dimensions",
    "ordinal_intensity_like_dimensions",
    "latent_pragmatic_attributes",
)

CUE_TYPES = (
    "explicit_lexical_cue",
    "compositional_cue",
    "pragmatic_inference",
    "world_background_knowledge",
    "discourse_context_dependence",
)

REJECTED_MICRO_FIXES = {
    "another_function_head": False,
    "tune_thresholds": False,
    "modify_ontology": False,
    "add_function_data_by_default": False,
    "use_QUAL_003_for_optimization": False,
    "reopen_encoder_selection": False,
    "retrain_DOMAIN_or_MEDIATION": False,
    "modify_NONE_gate": False,
}

# Heuristic thresholds for signal classification (diagnostic, not optimization).
MIN_SUPPORT_TRAIN = 40
MIN_SUPPORT_REP = 12
STRONG_F1 = 0.40
WEAK_F1 = 0.20
OVERLAP_JACCARD = 0.45
CONSENSUS_FAIL_SHARE = 0.40
MARGIN_WEAK = 0.05


def _hash(payload: Any) -> str:
    return sha256_text(canonical_json(payload))


def reassess_contract() -> dict[str, Any]:
    return {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "parent": {
            "phase": "REDESIGN_V6_FUNCTION_PREDICTION",
            "outcome": PARENT_REDESIGN_OUTCOME,
            "selected": PARENT_SELECTED,
            "baseline_FUNCTION": BASELINE_REP_V3["FUNCTION_macro_f1"],
            "independent_FUNCTION": 0.29381283709203987,
        },
        "surfaces": {
            "TRAIN": TRAIN_V3_ID,
            "DEV_SELECTION": DEV_V3_ID,
            "REPRESENTATIVE_VALIDATION": REP_V3_ID,
        },
        "frozen": {
            "encoder_model_id": SELECTED_ENCODER_MODEL_ID,
            "encoder_revision": SELECTED_ENCODER_REVISION,
            "ANY_LABEL_threshold": WITNESS_GATE_THRESHOLD,
            "ontology_changed": False,
            "operating_package_sha256": EXPECTED_PACKAGE_SHA256,
        },
        "function_vocab": list(FUNCTION_VOCAB),
        "function_definitions": dict(FUNCTION_DEFINITIONS),
        "formulations_compared": ["OLD_SHARED_HEAD", *FORMULATIONS],
        "signal_classes": list(SIGNAL_CLASSES),
        "ceiling_classes": list(CEILING_CLASSES),
        "diagnoses": list(DIAGNOSES),
        "next_actions": list(NEXT_ACTIONS),
        "axis_structures": list(AXIS_STRUCTURES),
        "cue_types": list(CUE_TYPES),
        "forbidden": [
            "design_another_function_head",
            "tune_thresholds",
            "modify_ontology",
            "add_function_data_by_default",
            "use_QUAL_003_for_optimization",
            "reopen_encoder_selection",
        ],
        "historical_qual": {
            "QUALIFICATION_ID": QUALIFICATION_ID,
            "seal_sha256": EXPECTED_SEAL_SHA256,
            "result_sha256": EXPECTED_QUAL_RESULT_SHA256,
            "role": "BLOCKED_SPENT_SURFACE",
        },
        "QUALIFICATION_USED_FOR_OPTIMIZATION": False,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "RELEASE_ELIGIBLE": False,
        "rejected_micro_fixes_default": dict(REJECTED_MICRO_FIXES),
    }


def classify_function_signal(audit: Mapping[str, Any]) -> str:
    """Map per-function forensic stats to a signal class."""
    support_train = int(audit.get("train_support") or 0)
    support_rep = int(audit.get("rep_support") or 0)
    f1_old = float(audit.get("old_head_f1") or 0.0)
    f1_ind = float(audit.get("independent_f1") or 0.0)
    best_f1 = max(f1_old, f1_ind, float(audit.get("hybrid_f1") or 0.0))
    margin = audit.get("pos_neg_margin")
    nn_purity = audit.get("nn_purity")
    overlap = float(audit.get("adjacent_overlap_rate") or 0.0)
    cue_prag = float(audit.get("pragmatic_or_context_share") or 0.0)
    consensus_fail = float(audit.get("consensus_fail_share_among_gold") or 0.0)
    agree = audit.get("human_function_jaccard")

    if support_train < MIN_SUPPORT_TRAIN or support_rep < MIN_SUPPORT_REP:
        return "INSUFFICIENT_SUPPORT"
    if overlap >= OVERLAP_JACCARD and best_f1 < STRONG_F1:
        return "SEMANTICALLY_OVERLAPPING"
    if cue_prag >= 0.45 or consensus_fail >= CONSENSUS_FAIL_SHARE:
        return "CONTEXT_SENSITIVE"
    if best_f1 >= STRONG_F1 and (
        margin is None or float(margin) >= MARGIN_WEAK
    ) and (nn_purity is None or float(nn_purity) >= 0.35):
        return "STRONG_TEXT_SIGNAL"
    if best_f1 >= WEAK_F1:
        return "WEAK_BUT_LEARNABLE"
    if agree is not None and float(agree) >= 0.9 and best_f1 < WEAK_F1:
        return "CONTEXT_SENSITIVE"
    return "WEAK_BUT_LEARNABLE"


def classify_ceiling(audit: Mapping[str, Any]) -> str:
    formulations = dict(audit.get("formulation_function_macros") or {})
    vals = [float(v) for v in formulations.values() if v is not None]
    if len(vals) < 2:
        return "NO_CLEAR_CEILING"
    top = max(vals)
    # Cluster among competitive formulations only; clear underperformers
    # (e.g. semantic matching << baseline) must not inflate the spread.
    competitive = [v for v in vals if v >= top - 0.05] or [top]
    if len(competitive) < 2:
        competitive = sorted(vals, reverse=True)[: min(3, len(vals))]
    spread = max(competitive) - min(competitive)
    full_spread = max(vals) - min(vals)
    consensus = float(audit.get("mean_consensus_fail_share") or 0.0)
    prag = float(audit.get("mean_pragmatic_share") or 0.0)
    agree = audit.get("mean_human_function_jaccard")
    support_ok = bool(audit.get("diversity_adequate", True))

    clustered_near_030 = top < 0.35 and spread < 0.08 and len(competitive) >= 2
    if not support_ok:
        return "DATA_LIMITED_CEILING"
    if agree is not None and float(agree) < 0.85 and clustered_near_030:
        return "ANNOTATION_BOUNDARY_CEILING"
    if clustered_near_030 and (consensus >= 0.35 or prag >= 0.40):
        return "TEXT_SIGNAL_CEILING"
    if clustered_near_030:
        return "MIXED_CEILING"
    if full_spread >= 0.10 and not clustered_near_030:
        return "NO_CLEAR_CEILING"
    return "MIXED_CEILING"


def classify_axis_structure(per_function: Mapping[str, Any]) -> str:
    classes = [dict(v).get("signal_class") for v in per_function.values()]
    overlapping = sum(1 for c in classes if c == "SEMANTICALLY_OVERLAPPING")
    context = sum(1 for c in classes if c == "CONTEXT_SENSITIVE")
    strong = sum(1 for c in classes if c == "STRONG_TEXT_SIGNAL")
    if overlapping >= 2:
        return "soft_overlapping_dimensions"
    if context >= 2:
        return "latent_pragmatic_attributes"
    if strong >= 3:
        return "independent_binary_predicates"
    if len(set(classes)) >= 3:
        return "latent_pragmatic_attributes"
    return "independent_binary_predicates"


def derive_diagnosis(audit: Mapping[str, Any]) -> dict[str, Any]:
    per = dict(audit.get("per_function") or {})
    classes = [dict(v).get("signal_class") for v in per.values()]
    ceiling = audit.get("ceiling_class") or classify_ceiling(audit)
    axis = audit.get("axis_structure") or classify_axis_structure(per)
    consensus_task_limit = bool(audit.get("task_signal_limit"))
    n_strong = sum(1 for c in classes if c == "STRONG_TEXT_SIGNAL")
    n_weak = sum(1 for c in classes if c == "WEAK_BUT_LEARNABLE")
    n_ctx = sum(1 for c in classes if c in {"CONTEXT_SENSITIVE", "SEMANTICALLY_OVERLAPPING"})
    n_insuff = sum(1 for c in classes if c == "INSUFFICIENT_SUPPORT")
    distinct_regimes = len({c for c in classes if c})

    if n_insuff >= 2 and not consensus_task_limit:
        diagnosis = "FUNCTION_TASK_SIGNAL_INSUFFICIENT"
        next_action = "TARGETED_FUNCTION_SUPPORT_EXPANSION"
    elif n_strong >= 3 and ceiling == "NO_CLEAR_CEILING":
        diagnosis = "FUNCTION_TASK_SIGNAL_SUPPORTED"
        next_action = "REDESIGN_V6_FUNCTION_OBJECTIVE_AROUND_PRAGMATIC_SIGNAL"
    elif n_ctx >= 2 or consensus_task_limit or ceiling in {
        "TEXT_SIGNAL_CEILING",
        "MIXED_CEILING",
        "ANNOTATION_BOUNDARY_CEILING",
    }:
        diagnosis = "FUNCTION_TASK_SIGNAL_PARTIAL"
        if distinct_regimes >= 3:
            next_action = "SPLIT_V6_FUNCTIONS_BY_SIGNAL_REGIME"
        elif ceiling == "TEXT_SIGNAL_CEILING" and n_strong == 0 and n_weak <= 1:
            next_action = "REASSESS_V6_FUNCTION_PRODUCT_REQUIREMENT"
        else:
            next_action = "REDESIGN_V6_FUNCTION_OBJECTIVE_AROUND_PRAGMATIC_SIGNAL"
    elif n_insuff >= 1:
        diagnosis = "FUNCTION_TASK_SIGNAL_PARTIAL"
        next_action = "TARGETED_FUNCTION_SUPPORT_EXPANSION"
    else:
        diagnosis = "FUNCTION_TASK_SIGNAL_PARTIAL"
        next_action = "REDESIGN_V6_FUNCTION_OBJECTIVE_AROUND_PRAGMATIC_SIGNAL"

    # Override: material regime split across functions
    if distinct_regimes >= 3 and diagnosis != "FUNCTION_TASK_SIGNAL_INSUFFICIENT":
        next_action = "SPLIT_V6_FUNCTIONS_BY_SIGNAL_REGIME"

    return {
        "PRIMARY_DIAGNOSIS": diagnosis,
        "CEILING_CLASS": ceiling,
        "AXIS_STRUCTURE": axis,
        "NEXT_ACTION": next_action,
        "signal_class_counts": {
            "STRONG_TEXT_SIGNAL": n_strong,
            "WEAK_BUT_LEARNABLE": n_weak,
            "CONTEXT_SENSITIVE": sum(1 for c in classes if c == "CONTEXT_SENSITIVE"),
            "SEMANTICALLY_OVERLAPPING": sum(
                1 for c in classes if c == "SEMANTICALLY_OVERLAPPING"
            ),
            "INSUFFICIENT_SUPPORT": n_insuff,
        },
        "task_signal_limit": consensus_task_limit,
    }


def build_reassess_receipt(
    audit: Mapping[str, Any], *, reviewed_at: str
) -> dict[str, Any]:
    derived = derive_diagnosis(audit)
    body = {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "PRIMARY_DIAGNOSIS": derived["PRIMARY_DIAGNOSIS"],
        "CEILING_CLASS": derived["CEILING_CLASS"],
        "AXIS_STRUCTURE": derived["AXIS_STRUCTURE"],
        "NEXT_ACTION": derived["NEXT_ACTION"],
        "signal_class_counts": derived["signal_class_counts"],
        "task_signal_limit": derived["task_signal_limit"],
        "audit": dict(audit),
        "REJECTED_MICRO_FIXES": dict(REJECTED_MICRO_FIXES),
        "QUALIFICATION_USED_FOR_OPTIMIZATION": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "RELEASE_ELIGIBLE": False,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "DOMAIN_HEAD_MUTATED": False,
        "MEDIATION_HEAD_MUTATED": False,
        "NONE_GATE_MUTATED": False,
        "ENCODER_MUTATED": False,
        "ONTOLOGY_MUTATED": False,
        "FUNCTION_HEAD_REDESIGNED": False,
        "reviewed_at": reviewed_at,
    }
    body["SYSTEM_TASK_SIGNAL_RECEIPT_SHA256"] = _hash(
        {k: v for k, v in body.items() if k != "SYSTEM_TASK_SIGNAL_RECEIPT_SHA256"}
    )
    return body


__all__ = [
    "AXIS_STRUCTURES",
    "CEILING_CLASSES",
    "CUE_TYPES",
    "DIAGNOSES",
    "EXPERIMENT_ID",
    "NEXT_ACTIONS",
    "PHASE_RULE",
    "REJECTED_MICRO_FIXES",
    "SIGNAL_CLASSES",
    "build_reassess_receipt",
    "classify_axis_structure",
    "classify_ceiling",
    "classify_function_signal",
    "derive_diagnosis",
    "reassess_contract",
]
