"""EXECUTE_V6_QUALIFICATION_003_ONCE — contracts.

One-shot scoring of HYPERLEX_V6_QUALIFICATION_003 against the hardened
operating pipeline package (encoder → ANY_LABEL gate → heads → hierarchy).
No retrain / recalibrate / ontology change / QUAL mutation.
"""

from __future__ import annotations

from typing import Any, Mapping

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
from .classification_v6_operating_pipeline_harden import (
    OPERATING_QUALIFICATION_GATES,
    PACKAGE_ID,
    PIPELINE_CANDIDATE_ID,
    RUNTIME_SCHEMA,
    WITNESS_GATE_BUNDLE_SHA256,
    WITNESS_GATE_THRESHOLD,
    WITNESS_REP_POSITIVE_ONLY,
    WITNESS_REP_SYSTEM_MACRO_F1,
    WITNESS_REP_ZERO_EXACT,
    WITNESS_REP_ZERO_FP,
    operating_error_taxonomy,
    operating_qualification_metrics,
)
from .classification_v6_qualification_execute_002 import (
    EXPECTED_ENCODER_STATE_HASH,
    EXPECTED_HEAD_BUNDLE_SHA256,
    exact_int_equals,
)
from .classification_v6_qualification_surface_003 import (
    EXPERIMENT_ID as SURFACE_EXPERIMENT_ID,
    OPERATING_PACKAGE_SHA256,
    QUALIFICATION_ID,
)
from .classification_v6_semantic_pipeline_harden import (
    SELECTED_ENCODER_MODEL_ID,
    SELECTED_ENCODER_REVISION,
)

PHASE_RULE = "EXECUTE_V6_QUALIFICATION_003_ONCE"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-QUALIFICATION-EXECUTE-003"
RESULT_ID = "HYPERLEX_V6_QUALIFICATION_003_RESULT"
SCHEMA = "hyperlex.classification.v6.qualification_execute_003.v1"

EXPECTED_SEAL_SHA256 = (
    "ae07e94fd492b7ef6c53a2034428b921ff4ae371eadf4a5a2448c85aad1cd27b"
)
EXPECTED_PACKAGE_SHA256 = OPERATING_PACKAGE_SHA256
EXPECTED_N_ROWS = 1151
EXPECTED_GATE_BUNDLE_SHA256 = WITNESS_GATE_BUNDLE_SHA256
EXPECTED_GATE_THRESHOLD = WITNESS_GATE_THRESHOLD

# Frozen REP_V2 operating witness (diagnostic retention only).
REP_REFERENCE_SYSTEM_MACRO_F1 = WITNESS_REP_SYSTEM_MACRO_F1
REP_REFERENCE_ZERO_FP = WITNESS_REP_ZERO_FP
REP_REFERENCE_POSITIVE_ONLY = WITNESS_REP_POSITIVE_ONLY
REP_REFERENCE_ZERO_EXACT = WITNESS_REP_ZERO_EXACT

RETENTION_BANDS = {
    "STRONG_RETENTION": 0.85,
    "MODERATE_RETENTION": 0.70,
    "SEVERE_GENERALIZATION_DROP": 0.0,
}

DISPOSITIONS = (
    "V6_QUALIFICATION_003_PASS",
    "V6_QUALIFICATION_003_FAIL",
    "V6_QUALIFICATION_003_INVALID",
)


def _hash(payload: Any) -> str:
    return sha256_text(canonical_json(payload))


def execute_contract() -> dict[str, Any]:
    return {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "RESULT_ID": RESULT_ID,
        "surface_experiment": SURFACE_EXPERIMENT_ID,
        "PACKAGE_ID": PACKAGE_ID,
        "PIPELINE_CANDIDATE_ID": PIPELINE_CANDIDATE_ID,
        "runtime_schema": RUNTIME_SCHEMA,
        "expected": {
            "seal_sha256": EXPECTED_SEAL_SHA256,
            "package_sha256": EXPECTED_PACKAGE_SHA256,
            "n_rows": EXPECTED_N_ROWS,
            "head_bundle_sha256": EXPECTED_HEAD_BUNDLE_SHA256,
            "gate_bundle_sha256": EXPECTED_GATE_BUNDLE_SHA256,
            "gate_threshold": EXPECTED_GATE_THRESHOLD,
            "encoder_state_hash": EXPECTED_ENCODER_STATE_HASH,
            "encoder_model_id": SELECTED_ENCODER_MODEL_ID,
            "encoder_revision": SELECTED_ENCODER_REVISION,
            "encoder_trainable_parameters": 0,
            "qualification_model_executions_before": 0,
            "qualification_state_before": "SEALED_UNSCORED",
        },
        "gates": dict(OPERATING_QUALIFICATION_GATES),
        "metrics": operating_qualification_metrics(),
        "error_taxonomy": operating_error_taxonomy(),
        "retention": {
            "rep_reference_system_macro_f1": REP_REFERENCE_SYSTEM_MACRO_F1,
            "rep_reference_zero_fp": REP_REFERENCE_ZERO_FP,
            "rep_reference_positive_only": REP_REFERENCE_POSITIVE_ONLY,
            "rep_reference_zero_exact": REP_REFERENCE_ZERO_EXACT,
            "bands": dict(RETENTION_BANDS),
            "hard_gate": False,
        },
        "forbidden": [
            "retrain",
            "recalibrate",
            "adjust_ANY_LABEL_threshold",
            "modify_axis_heads",
            "modify_ontology",
            "alter_hierarchy",
            "modify_QUAL_003_rows_or_gold",
            "inspect_or_reuse_QUAL_002",
            "exploratory_retries",
            "subset_reruns",
            "mutate_MODEL_WIDE_BEST",
            "mutate_global_pointers",
            "auto_publish",
        ],
        "pointer_policy": {
            "MODEL_WIDE_BEST": "UNCHANGED",
            "V6_OPERATING_PIPELINE_CANDIDATE": "UNCHANGED",
            "V5_pointers": "UNCHANGED",
        },
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "HUB_PUBLISH_AUTHORIZED": False,
    }


def classify_retention(
    qual_macro: float, *, rep_macro: float = REP_REFERENCE_SYSTEM_MACRO_F1
) -> dict[str, Any]:
    ratio = float(qual_macro) / max(1e-12, float(rep_macro))
    drop = float(rep_macro) - float(qual_macro)
    if ratio >= RETENTION_BANDS["STRONG_RETENTION"]:
        band = "STRONG_RETENTION"
    elif ratio >= RETENTION_BANDS["MODERATE_RETENTION"]:
        band = "MODERATE_RETENTION"
    else:
        band = "SEVERE_GENERALIZATION_DROP"
    return {
        "qual_system_macro_f1": float(qual_macro),
        "rep_system_macro_f1": float(rep_macro),
        "absolute_drop": drop,
        "retention_ratio": ratio,
        "band": band,
        "hard_gate": False,
    }


def axis_collapse_detected(
    axis_macros: Mapping[str, float], *, floor: float | None = None
) -> bool:
    floor = float(
        OPERATING_QUALIFICATION_GATES["min_axis_macro_f1"] if floor is None else floor
    )
    for axis in ("domain", "function", "mediation"):
        if float(axis_macros.get(axis) or 0.0) < floor:
            return True
    return False


def evaluate_operating_gates(
    *,
    system_macro_f1: float,
    hierarchy_violation: float,
    axis_macros: Mapping[str, float],
    zero_label_false_positive_rate: float,
    zero_label_exact_rejection: float,
    positive_only_system_macro_f1: float,
    mean_predicted_labels_on_zero_gold: float | None = None,
) -> dict[str, Any]:
    collapse = axis_collapse_detected(axis_macros)
    g = OPERATING_QUALIFICATION_GATES
    gates = {
        "system_macro_f1": {
            "value": float(system_macro_f1),
            "threshold": float(g["system_macro_f1_min"]),
            "pass": float(system_macro_f1) >= float(g["system_macro_f1_min"]),
        },
        "hierarchy_violation": {
            "value": float(hierarchy_violation),
            "threshold": float(g["hierarchy_violation_max"]),
            "pass": float(hierarchy_violation) <= float(g["hierarchy_violation_max"]),
        },
        "no_material_axis_collapse": {
            "value": not collapse,
            "threshold": float(g["min_axis_macro_f1"]),
            "axis_macros": {k: float(v) for k, v in axis_macros.items()},
            "pass": not collapse,
        },
        "zero_label_false_positive_rate": {
            "value": float(zero_label_false_positive_rate),
            "threshold": float(g["zero_label_false_positive_rate_max"]),
            "pass": float(zero_label_false_positive_rate)
            <= float(g["zero_label_false_positive_rate_max"]),
        },
        "zero_label_exact_rejection": {
            "value": float(zero_label_exact_rejection),
            "threshold": float(g["zero_label_exact_rejection_min"]),
            "pass": float(zero_label_exact_rejection)
            >= float(g["zero_label_exact_rejection_min"]),
        },
        "positive_only_system_macro_f1": {
            "value": float(positive_only_system_macro_f1),
            "threshold": float(g["positive_only_system_macro_f1_min"]),
            "pass": float(positive_only_system_macro_f1)
            >= float(g["positive_only_system_macro_f1_min"]),
        },
    }
    if mean_predicted_labels_on_zero_gold is not None:
        gates["mean_predicted_labels_on_zero_gold"] = {
            "value": float(mean_predicted_labels_on_zero_gold),
            "threshold": float(g["mean_predicted_labels_on_zero_gold_max"]),
            "pass": float(mean_predicted_labels_on_zero_gold)
            <= float(g["mean_predicted_labels_on_zero_gold_max"]),
            "advisory": True,
        }
    # Hard gates exclude advisory mean-pred-on-zero (keep preregistered user gates).
    hard_keys = [
        "system_macro_f1",
        "hierarchy_violation",
        "no_material_axis_collapse",
        "zero_label_false_positive_rate",
        "zero_label_exact_rejection",
        "positive_only_system_macro_f1",
    ]
    overall = all(gates[k]["pass"] for k in hard_keys)
    return {"gates": gates, "pass": overall}


def decide_disposition(
    *,
    preflight_ok: bool,
    execution_ok: bool,
    gate_pass: bool,
) -> dict[str, Any]:
    if not preflight_ok or not execution_ok:
        return {
            "QUALIFICATION_DISPOSITION": "V6_QUALIFICATION_003_INVALID",
            "RELEASE_ELIGIBLE": False,
            "NEXT_ACTION": "REPAIR_V6_QUALIFICATION_003_EXECUTION",
            "HUB_PUBLISH_AUTHORIZED": False,
        }
    if gate_pass:
        return {
            "QUALIFICATION_DISPOSITION": "V6_QUALIFICATION_003_PASS",
            "RELEASE_ELIGIBLE": True,
            "NEXT_ACTION": "PREPARE_HYPERLEX_V6_RELEASE_CANDIDATE",
            "HUB_PUBLISH_AUTHORIZED": False,
        }
    return {
        "QUALIFICATION_DISPOSITION": "V6_QUALIFICATION_003_FAIL",
        "RELEASE_ELIGIBLE": False,
        "NEXT_ACTION": "REVIEW_V6_QUALIFICATION_003_FAILURE",
        "HUB_PUBLISH_AUTHORIZED": False,
    }


__all__ = [
    "DISPOSITIONS",
    "EXPERIMENT_ID",
    "EXPECTED_GATE_BUNDLE_SHA256",
    "EXPECTED_GATE_THRESHOLD",
    "EXPECTED_N_ROWS",
    "EXPECTED_PACKAGE_SHA256",
    "EXPECTED_SEAL_SHA256",
    "PHASE_RULE",
    "QUALIFICATION_ID",
    "REP_REFERENCE_POSITIVE_ONLY",
    "REP_REFERENCE_SYSTEM_MACRO_F1",
    "REP_REFERENCE_ZERO_EXACT",
    "REP_REFERENCE_ZERO_FP",
    "RESULT_ID",
    "axis_collapse_detected",
    "classify_retention",
    "decide_disposition",
    "evaluate_operating_gates",
    "exact_int_equals",
    "execute_contract",
]
