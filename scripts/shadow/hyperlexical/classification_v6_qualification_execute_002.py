"""EXECUTE_V6_FRESH_QUALIFICATION_ONCE — contracts.

One-shot scoring of HYPERLEX_V6_QUALIFICATION_002 against the hardened
V6 semantic pipeline package. No retrain / recalibrate / ontology change.
"""

from __future__ import annotations

from typing import Any, Mapping

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
from .classification_v6_qualification_surface_002 import (
    EXPERIMENT_ID as SURFACE_EXPERIMENT_ID,
    QUALIFICATION_ID,
)
from .classification_v6_semantic_pipeline_harden import (
    ERROR_TAXONOMY,
    PACKAGE_ID,
    PIPELINE_CANDIDATE_ID,
    QUALIFICATION_GATES,
    RUNTIME_SCHEMA,
    SELECTED_ENCODER_MODEL_ID,
    SELECTED_ENCODER_REVISION,
    THRESHOLD_MANIFEST_ID,
    pipeline_candidate_contract,
    qualification_preregistration,
)

PHASE_RULE = "EXECUTE_V6_FRESH_QUALIFICATION_ONCE"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-QUALIFICATION-EXECUTE-002"
RESULT_ID = "HYPERLEX_V6_QUALIFICATION_002_RESULT"
SCHEMA = "hyperlex.classification.v6.qualification_execute_002.v1"

EXPECTED_SEAL_SHA256 = (
    "62ed3827fb751c52d3e679ec4e1e2df2b20ea674326fa1dd9ee9567fe4883874"
)
EXPECTED_PACKAGE_SHA256 = (
    "a88275837b341b4c549a9c973f5c5190a8f3878be57dffd302e72269d2d560c4"
)
EXPECTED_N_ROWS = 1004
EXPECTED_HEAD_BUNDLE_SHA256 = (
    "2a0724b5a22b67523d56b8a0117533e4d4d63bf2f775f78097735f9518b64942"
)
EXPECTED_ENCODER_STATE_HASH = (
    "586fe515fa74674a62563cedbf65262fbfe165f9edefed1928029865a12e0a53"
)
REP_REFERENCE_SYSTEM_MACRO_F1 = 0.4322391331580084

# Descriptive retention bands (preregistered; not a hard gate).
RETENTION_BANDS = {
    "STRONG_RETENTION": 0.85,
    "MODERATE_RETENTION": 0.70,
    "SEVERE_GENERALIZATION_DROP": 0.0,
}

DISPOSITIONS = (
    "V6_QUALIFICATION_PASS",
    "V6_QUALIFICATION_FAIL",
    "V6_QUALIFICATION_INVALID",
)

LABEL_CLASSES = ("STABLE", "DEGRADED", "LOW_SUPPORT", "FAILED")
SOURCE_CLASSES = ("SOURCE_STABLE", "SOURCE_SENSITIVE", "SOURCE_COLLAPSE")


def _hash(payload: Any) -> str:
    return sha256_text(canonical_json(payload))


def execute_contract() -> dict[str, Any]:
    cand = pipeline_candidate_contract()
    return {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "RESULT_ID": RESULT_ID,
        "surface_experiment": SURFACE_EXPERIMENT_ID,
        "PACKAGE_ID": PACKAGE_ID,
        "PIPELINE_CANDIDATE_ID": PIPELINE_CANDIDATE_ID,
        "expected": {
            "seal_sha256": EXPECTED_SEAL_SHA256,
            "package_sha256": EXPECTED_PACKAGE_SHA256,
            "n_rows": EXPECTED_N_ROWS,
            "head_bundle_sha256": EXPECTED_HEAD_BUNDLE_SHA256,
            "encoder_state_hash": EXPECTED_ENCODER_STATE_HASH,
            "encoder_model_id": SELECTED_ENCODER_MODEL_ID,
            "encoder_revision": SELECTED_ENCODER_REVISION,
            "encoder_trainable_parameters": 0,
            "qualification_model_executions_before": 0,
            "qualification_state_before": "SEALED_UNSCORED",
        },
        "gates": dict(QUALIFICATION_GATES),
        "qualification_preregistration": qualification_preregistration(),
        "error_taxonomy": list(ERROR_TAXONOMY),
        "retention": {
            "rep_reference_system_macro_f1": REP_REFERENCE_SYSTEM_MACRO_F1,
            "bands": dict(RETENTION_BANDS),
            "hard_gate": False,
        },
        "runtime_schema": RUNTIME_SCHEMA,
        "threshold_manifest_id": THRESHOLD_MANIFEST_ID,
        "pipeline_candidate_ref": cand["PIPELINE_CANDIDATE_ID"],
        "forbidden": [
            "retrain",
            "recalibrate",
            "adjust_thresholds",
            "modify_ontology",
            "alter_hierarchy",
            "modify_QUAL_rows_or_gold",
            "inspect_QUAL_001",
            "exploratory_retries",
            "select_different_encoder_after_results",
            "mutate_MODEL_WIDE_BEST",
            "mutate_V5_pointers",
            "auto_publish",
        ],
        "pointer_policy": {
            "MODEL_WIDE_BEST": "UNCHANGED",
            "STAGE_A_BEST": "UNCHANGED",
            "V5_pointers": "UNCHANGED",
            "V6_REPRESENTATION_CANDIDATE_on_pass": "QUALIFICATION_PASSED",
            "V6_REPRESENTATION_CANDIDATE_on_fail": "QUALIFICATION_FAILED",
        },
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "HUB_PUBLISH_AUTHORIZED": False,
    }


def classify_retention(qual_macro: float, *, rep_macro: float = REP_REFERENCE_SYSTEM_MACRO_F1) -> dict[str, Any]:
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


def classify_qual_label(
    *,
    qual_f1: float,
    support: int,
    rep_f1: float | None = None,
    min_support: int = 10,
) -> str:
    if support < min_support:
        return "LOW_SUPPORT"
    if qual_f1 < 0.05:
        return "FAILED"
    if rep_f1 is not None and support >= min_support and (rep_f1 - qual_f1) >= 0.25:
        return "DEGRADED"
    if qual_f1 < 0.20:
        return "DEGRADED"
    return "STABLE"


def axis_collapse_detected(axis_macros: Mapping[str, float], *, floor: float | None = None) -> bool:
    floor = float(QUALIFICATION_GATES["min_axis_macro_f1"] if floor is None else floor)
    for axis in ("domain", "function", "mediation"):
        if float(axis_macros.get(axis) or 0.0) < floor:
            return True
    return False


def evaluate_gates(
    *,
    system_macro_f1: float,
    hierarchy_violation: float,
    axis_macros: Mapping[str, float],
) -> dict[str, Any]:
    collapse = axis_collapse_detected(axis_macros)
    gates = {
        "system_macro_f1": {
            "value": float(system_macro_f1),
            "threshold": float(QUALIFICATION_GATES["system_macro_f1_min"]),
            "pass": float(system_macro_f1) >= float(QUALIFICATION_GATES["system_macro_f1_min"]),
        },
        "hierarchy_violation": {
            "value": float(hierarchy_violation),
            "threshold": float(QUALIFICATION_GATES["hierarchy_violation_max"]),
            "pass": float(hierarchy_violation)
            <= float(QUALIFICATION_GATES["hierarchy_violation_max"]),
        },
        "no_material_axis_collapse": {
            "value": not collapse,
            "threshold": float(QUALIFICATION_GATES["min_axis_macro_f1"]),
            "axis_macros": {k: float(v) for k, v in axis_macros.items()},
            "pass": not collapse,
        },
    }
    overall = all(g["pass"] for g in gates.values())
    return {"gates": gates, "pass": overall}


def decide_disposition(
    *,
    preflight_ok: bool,
    execution_ok: bool,
    gate_pass: bool,
) -> dict[str, Any]:
    if not preflight_ok or not execution_ok:
        return {
            "QUALIFICATION_DISPOSITION": "V6_QUALIFICATION_INVALID",
            "RELEASE_ELIGIBLE": False,
            "V6_REPRESENTATION_CANDIDATE_STATUS": "QUALIFICATION_FAILED",
            "NEXT_ACTION": "REPAIR_V6_QUALIFICATION_EXECUTION",
            "HUB_PUBLISH_AUTHORIZED": False,
        }
    if gate_pass:
        return {
            "QUALIFICATION_DISPOSITION": "V6_QUALIFICATION_PASS",
            "RELEASE_ELIGIBLE": True,
            "V6_REPRESENTATION_CANDIDATE_STATUS": "QUALIFICATION_PASSED",
            "NEXT_ACTION": "PREPARE_HYPERLEX_V6_RELEASE_CANDIDATE",
            "HUB_PUBLISH_AUTHORIZED": False,
        }
    return {
        "QUALIFICATION_DISPOSITION": "V6_QUALIFICATION_FAIL",
        "RELEASE_ELIGIBLE": False,
        "V6_REPRESENTATION_CANDIDATE_STATUS": "QUALIFICATION_FAILED",
        "NEXT_ACTION": "REVIEW_V6_QUALIFICATION_FAILURE_AT_SYSTEM_LEVEL",
        "HUB_PUBLISH_AUTHORIZED": False,
    }


def exact_int_equals(value: Any, expected: int) -> bool:
    """True iff value is present and equals expected.

    Must not use ``value or default`` — zero is a valid witness
    (forbidden_overlap=0, trainable_parameters=0).
    """
    if value is None:
        return False
    try:
        return int(value) == int(expected)
    except (TypeError, ValueError):
        return False


def classify_source_slice(
    family_macros: Mapping[str, float],
    *,
    system_macro: float,
) -> str:
    vals = [float(v) for v in family_macros.values() if v is not None]
    if not vals:
        return "SOURCE_SENSITIVE"
    spread = max(vals) - min(vals)
    collapsed = sum(1 for v in vals if v < 0.05)
    if collapsed >= max(1, len(vals) // 2) or (system_macro > 0 and min(vals) < 0.25 * system_macro and spread > 0.40):
        return "SOURCE_COLLAPSE"
    if spread <= 0.15 and collapsed == 0:
        return "SOURCE_STABLE"
    return "SOURCE_SENSITIVE"


__all__ = [
    "DISPOSITIONS",
    "ERROR_TAXONOMY",
    "EXPERIMENT_ID",
    "EXPECTED_N_ROWS",
    "EXPECTED_PACKAGE_SHA256",
    "EXPECTED_SEAL_SHA256",
    "PHASE_RULE",
    "QUALIFICATION_ID",
    "REP_REFERENCE_SYSTEM_MACRO_F1",
    "RESULT_ID",
    "axis_collapse_detected",
    "classify_qual_label",
    "classify_retention",
    "classify_source_slice",
    "decide_disposition",
    "evaluate_gates",
    "exact_int_equals",
    "execute_contract",
]
