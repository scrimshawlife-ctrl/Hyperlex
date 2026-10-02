"""HARDEN_V6_NONE_REJECTION_UNDER_FROZEN_ENCODER — contracts.

Bounded phase: improve zero-label / NO_EVIDENCE rejection under the frozen
semantic encoder and sealed TRAIN_V2/DEV_V2/REP_V2 surfaces. QUAL-002 stays
EVALUATION_SPENT and is not used for optimization. MODEL_WIDE_BEST unchanged.
"""

from __future__ import annotations

from typing import Any, Mapping

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
from .classification_v6_qualification_execute_002 import (
    EXPECTED_ENCODER_STATE_HASH,
    EXPECTED_PACKAGE_SHA256,
)
from .classification_v6_representative_validation_redesign import (
    DEV_V2_ID,
    REP_V2_ID,
    TRAIN_V2_ID,
)
from .classification_v6_semantic_pipeline_harden import (
    PACKAGE_ID,
    SELECTED_ENCODER_MODEL_ID,
    SELECTED_ENCODER_REVISION,
)

PHASE_RULE = "HARDEN_V6_NONE_REJECTION_UNDER_FROZEN_ENCODER"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-NONE-REJECTION-HARDEN-001"
SCHEMA = "hyperlex.classification.v6.none_rejection_harden.v1"
CANDIDATE_PACKAGE_ID = "HYPERLEX_V6_NONE_REJECTION_PACKAGE_CANDIDATE_V1"
PIPELINE_POINTER_ID = "V6_NONE_REJECTION_CANDIDATE"

# Sealed REP_V2 baseline witnesses (frozen package a8827583… replay).
BASELINE_REP_SYSTEM_MACRO_F1 = 0.22031767868121946
BASELINE_REP_POSITIVE_ONLY_MACRO_F1 = 0.41630366884055453
BASELINE_REP_ZERO_FP_RATE = 0.7881548974943052
BASELINE_REP_ZERO_EXACT_REJECTION = 0.21184510250569477
BASELINE_REP_MEAN_PRED_ON_ZERO = 2.2687927107061503

# Preregistered acceptance (locked before results).
ZERO_FP_ABS_IMPROVEMENT_MIN = 0.15
ZERO_EXACT_ABS_IMPROVEMENT_MIN = 0.15
POSITIVE_PRESERVATION_RATIO = 0.90  # of baseline positive-only ≈0.416 → ≈0.375
FALSE_REJECT_POSITIVE_MAX = 0.35
SYSTEM_MACRO_FLOOR_RELATIVE = -0.02  # may not fall >2pp below baseline system

MECHANISMS = (
    "BASELINE_DIRECT_EMISSION",
    "LEARNED_ANY_EVIDENCE_GATE",
    "SHARED_MAX_SCORE_REJECT",
    "NEGATIVE_AWARE_HEAD_RETRAIN",
    "GATE_PLUS_NEGATIVE_AWARE_HEADS",
)

DISPOSITIONS = (
    "V6_NONE_REJECTION_ADVANCE",
    "V6_NONE_REJECTION_PARTIAL",
    "V6_NONE_REJECTION_NO_ADVANCE",
)

ERROR_CLASSES = (
    "FALSE_ACCEPT_ZERO",
    "FALSE_REJECT_POSITIVE",
    "POSITIVE_LABEL_FP",
    "POSITIVE_LABEL_FN",
    "FUNCTION_FAILURE",
    "CO_LABEL_FAILURE",
)


def none_rejection_contract() -> dict[str, Any]:
    return {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "surfaces": {
            "TRAIN": TRAIN_V2_ID,
            "DEV_SELECTION": DEV_V2_ID,
            "REPRESENTATIVE_VALIDATION": REP_V2_ID,
            "definitions_frozen": True,
        },
        "frozen": {
            "PACKAGE_SHA256": EXPECTED_PACKAGE_SHA256,
            "PACKAGE_ID": PACKAGE_ID,
            "encoder_model_id": SELECTED_ENCODER_MODEL_ID,
            "encoder_revision": SELECTED_ENCODER_REVISION,
            "encoder_state_hash": EXPECTED_ENCODER_STATE_HASH,
            "encoder_mutable": False,
            "ontology_changed": False,
            "retrain_encoder": False,
            "architecture_bakeoff": False,
        },
        "preferred_architecture": {
            "stages": [
                "frozen_embedding",
                "ANY_LABEL_ZERO_LABEL_gate",
                "if_ZERO_LABEL_emit_empty",
                "else_existing_axis_heads",
                "hierarchy_constraints",
            ],
            "compare_to": "BASELINE_DIRECT_EMISSION",
        },
        "mechanisms": list(MECHANISMS),
        "baseline_witnesses": {
            "REP_V2_system_macro_f1": BASELINE_REP_SYSTEM_MACRO_F1,
            "REP_V2_positive_only_system_macro_f1": BASELINE_REP_POSITIVE_ONLY_MACRO_F1,
            "REP_V2_zero_label_false_positive_rate": BASELINE_REP_ZERO_FP_RATE,
            "REP_V2_zero_label_exact_rejection": BASELINE_REP_ZERO_EXACT_REJECTION,
            "REP_V2_mean_predicted_labels_on_zero_gold": BASELINE_REP_MEAN_PRED_ON_ZERO,
        },
        "acceptance": {
            "zero_fp_abs_improvement_min": ZERO_FP_ABS_IMPROVEMENT_MIN,
            "zero_exact_abs_improvement_min": ZERO_EXACT_ABS_IMPROVEMENT_MIN,
            "positive_preservation_ratio": POSITIVE_PRESERVATION_RATIO,
            "positive_only_floor": BASELINE_REP_POSITIVE_ONLY_MACRO_F1
            * POSITIVE_PRESERVATION_RATIO,
            "false_reject_positive_max": FALSE_REJECT_POSITIVE_MAX,
            "system_macro_floor": BASELINE_REP_SYSTEM_MACRO_F1
            + SYSTEM_MACRO_FLOOR_RELATIVE,
            "reject_everything_forbidden": True,
            "optimize_aggregate_macro_only": False,
            "gates_locked_before_results": True,
        },
        "QUAL_002": {
            "role": "EVALUATION_SPENT_NO_OPTIMIZATION",
            "row_access": False,
        },
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "RELEASE_ELIGIBLE": False,
        "global_promotion": False,
    }


def zero_label_improved(metrics: Mapping[str, Any]) -> bool:
    zero_fp = float(metrics.get("zero_label_false_positive_rate") or 1.0)
    exact = float(metrics.get("zero_label_exact_rejection") or 0.0)
    mean_pred = float(metrics.get("mean_predicted_labels_on_zero_gold") or 99.0)
    fp_ok = zero_fp <= BASELINE_REP_ZERO_FP_RATE - ZERO_FP_ABS_IMPROVEMENT_MIN
    exact_ok = exact >= BASELINE_REP_ZERO_EXACT_REJECTION + ZERO_EXACT_ABS_IMPROVEMENT_MIN
    mean_ok = mean_pred <= BASELINE_REP_MEAN_PRED_ON_ZERO * 0.55
    return bool(fp_ok or exact_ok) and bool(mean_ok or fp_ok)


def positive_preserved(metrics: Mapping[str, Any]) -> bool:
    pos = float(metrics.get("positive_only_system_macro_f1") or 0.0)
    floor = BASELINE_REP_POSITIVE_ONLY_MACRO_F1 * POSITIVE_PRESERVATION_RATIO
    return pos >= floor


def not_reject_everything(metrics: Mapping[str, Any]) -> bool:
    fr = float(metrics.get("false_reject_positive_rate") or 1.0)
    pos = float(metrics.get("positive_only_system_macro_f1") or 0.0)
    return fr <= FALSE_REJECT_POSITIVE_MAX and pos >= 0.25


def classify_disposition(metrics: Mapping[str, Any]) -> dict[str, Any]:
    """Return ADVANCE / PARTIAL / NO_ADVANCE from preregistered rules."""
    z_ok = zero_label_improved(metrics)
    p_ok = positive_preserved(metrics)
    nr_ok = not_reject_everything(metrics)
    sys_m = float(metrics.get("system_macro_f1") or 0.0)
    sys_floor = BASELINE_REP_SYSTEM_MACRO_F1 + SYSTEM_MACRO_FLOOR_RELATIVE
    sys_ok = sys_m >= sys_floor

    if z_ok and p_ok and nr_ok and sys_ok:
        disposition = "V6_NONE_REJECTION_ADVANCE"
    elif z_ok and nr_ok:
        disposition = "V6_NONE_REJECTION_PARTIAL"
    else:
        disposition = "V6_NONE_REJECTION_NO_ADVANCE"

    return {
        "DISPOSITION": disposition,
        "zero_label_improved": z_ok,
        "positive_preserved": p_ok,
        "not_reject_everything": nr_ok,
        "system_floor_ok": sys_ok,
        "checks": {
            "zero_fp": float(metrics.get("zero_label_false_positive_rate") or 1.0),
            "zero_exact": float(metrics.get("zero_label_exact_rejection") or 0.0),
            "mean_pred_zero": float(
                metrics.get("mean_predicted_labels_on_zero_gold") or 99.0
            ),
            "positive_only": float(
                metrics.get("positive_only_system_macro_f1") or 0.0
            ),
            "false_reject_positive": float(
                metrics.get("false_reject_positive_rate") or 1.0
            ),
            "system_macro_f1": sys_m,
            "positive_floor": BASELINE_REP_POSITIVE_ONLY_MACRO_F1
            * POSITIVE_PRESERVATION_RATIO,
            "system_floor": sys_floor,
        },
    }


def decide_next_action(disposition: str, metrics: Mapping[str, Any]) -> str:
    if disposition == "V6_NONE_REJECTION_ADVANCE":
        fn = float(metrics.get("FUNCTION_macro_f1") or 0.0)
        pos = float(metrics.get("positive_only_system_macro_f1") or 0.0)
        if fn < 0.15 or pos < 0.30:
            return "HARDEN_V6_POSITIVE_SEMANTIC_GENERALIZATION"
        return "HARDEN_V6_FULL_OPERATING_PIPELINE_AND_PREPARE_NEW_QUALIFICATION"
    if disposition == "V6_NONE_REJECTION_PARTIAL":
        return "HARDEN_V6_POSITIVE_SEMANTIC_GENERALIZATION"
    return "REASSESS_V6_EVIDENCE_GATE_SIGNAL"


def build_none_rejection_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    body = dict(payload)
    body["MODEL_WIDE_BEST"] = MODEL_WIDE_BEST_SHA256
    body["MODEL_WIDE_BEST_MUTATED"] = False
    body["HUB_PUBLISH_AUTHORIZED"] = False
    body["RELEASE_ELIGIBLE"] = False
    body["QUAL_002_ROWS_USED_FOR_OPTIMIZATION"] = False
    body["encoder_mutable"] = False
    body["schema"] = SCHEMA
    body["V6_NONE_REJECTION_HARDEN_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in body.items()
                if k != "V6_NONE_REJECTION_HARDEN_RECEIPT_SHA256"
            }
        )
    )
    return body


__all__ = [
    "BASELINE_REP_MEAN_PRED_ON_ZERO",
    "BASELINE_REP_POSITIVE_ONLY_MACRO_F1",
    "BASELINE_REP_SYSTEM_MACRO_F1",
    "BASELINE_REP_ZERO_EXACT_REJECTION",
    "BASELINE_REP_ZERO_FP_RATE",
    "CANDIDATE_PACKAGE_ID",
    "DISPOSITIONS",
    "ERROR_CLASSES",
    "EXPERIMENT_ID",
    "FALSE_REJECT_POSITIVE_MAX",
    "MECHANISMS",
    "PHASE_RULE",
    "PIPELINE_POINTER_ID",
    "POSITIVE_PRESERVATION_RATIO",
    "SCHEMA",
    "SYSTEM_MACRO_FLOOR_RELATIVE",
    "ZERO_EXACT_ABS_IMPROVEMENT_MIN",
    "ZERO_FP_ABS_IMPROVEMENT_MIN",
    "build_none_rejection_receipt",
    "classify_disposition",
    "decide_next_action",
    "none_rejection_contract",
    "not_reject_everything",
    "positive_preserved",
    "zero_label_improved",
]
