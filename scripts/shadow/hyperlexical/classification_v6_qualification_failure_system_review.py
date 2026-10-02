"""REVIEW_V6_QUALIFICATION_FAILURE_AT_SYSTEM_LEVEL — contracts.

Read-only forensic review after HYPERLEX_V6_QUALIFICATION_002 FAIL.
Does not train, recalibrate, alter thresholds, create QUAL, or move pointers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
from .classification_v6_qualification_execute_002 import (
    EXPECTED_N_ROWS,
    EXPECTED_PACKAGE_SHA256,
    EXPECTED_SEAL_SHA256,
    QUALIFICATION_ID,
    REP_REFERENCE_SYSTEM_MACRO_F1,
    RESULT_ID,
)

REVIEW_RULE = "REVIEW_V6_QUALIFICATION_FAILURE_AT_SYSTEM_LEVEL"
REVIEW_ID = "HYPERLEX_V6_QUALIFICATION_FAILURE_SYSTEM_REVIEW_001"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-QUALIFICATION-FAILURE-SYSTEM-REVIEW-001"
SCHEMA = "hyperlex.classification.v6.qualification_failure_system_review.v1"

EXPECTED_QUAL_RESULT_SHA256 = (
    "73548c4331d7e471ba2251faef82fc38f64dde347999c0cf868a7b20b09f3fcd"
)

PRIMARY_DIAGNOSES = (
    "REPRESENTATIVE_VALIDATION_OVERFIT",
    "SEMANTIC_ENCODER_DOMAIN_MISMATCH",
    "AXIS_SPECIFIC_GENERALIZATION_FAILURE",
    "MULTI_LABEL_COMPOSITION_GENERALIZATION_FAILURE",
    "LABEL_PRIOR_CALIBRATION_FAILURE",
    "DATA_DIVERSITY_FAILURE",
    "TASK_SIGNAL_LIMITATION",
    "MIXED_V6_SYSTEM_GENERALIZATION_FAILURE",
)

V6_DISPOSITIONS = (
    "V6_RESEARCH_PROTOTYPE_CONTINUE",
    "V6_REQUIRES_REPRESENTATION_REDESIGN",
    "V6_REQUIRES_DATA_DISTRIBUTION_REDESIGN",
    "V6_REQUIRES_TASK_REDESIGN",
    "V6_ARCHIVE",
)

NEXT_PHASES = (
    "REDESIGN_V6_REPRESENTATIVE_VALIDATION_AND_DATA_DIVERSITY",
    "TEST_AXIS_SPECIFIC_SEMANTIC_ENCODERS",
    "REBASE_V6_ON_DIFFERENT_SEMANTIC_REPRESENTATION_FAMILY",
    "EXPAND_V6_NATURAL_DIVERSITY_BY_FAILURE_STRATA",
    "REASSESS_HYPERLEX_V6_TASK_DEFINITION",
    "ARCHIVE_V6_AND_PRESERVE_RESEARCH_FINDINGS",
)

REJECTED_MICRO_FIXES = {
    "threshold_retuning": False,
    "another_nonlinear_head_variant": False,
    "more_hidden_units": False,
    "another_optimizer": False,
    "another_seed_sweep": False,
    "another_REP_tuned_encoder": False,
    "simple_TRAIN_expansion": False,
    "another_QUAL_surface": False,
}

DROP_BANDS = {
    "STABLE": 0.85,
    "MODERATE_DROP": 0.70,
    "SEVERE_DROP": 0.35,
    "COLLAPSED": 0.0,
}


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            ("null" if key is None else str(key)): jsonable(value)
            for key, value in obj.items()
        }
    if isinstance(obj, (list, tuple)):
        return [jsonable(x) for x in obj]
    if isinstance(obj, float):
        if obj != obj or obj in (float("inf"), float("-inf")):
            return None
        return obj
    return obj


def classify_drop(rep: float | None, qual: float | None) -> str:
    if rep is None or qual is None:
        return "SEVERE_DROP"
    if float(rep) <= 1e-12:
        return "STABLE" if float(qual) <= 1e-12 else "MODERATE_DROP"
    ratio = float(qual) / float(rep)
    if ratio >= DROP_BANDS["STABLE"]:
        return "STABLE"
    if ratio >= DROP_BANDS["MODERATE_DROP"]:
        return "MODERATE_DROP"
    if ratio >= DROP_BANDS["SEVERE_DROP"] and float(qual) >= 0.05:
        return "SEVERE_DROP"
    return "COLLAPSED"


def classify_shift(
    *,
    jsd_or_l1: float,
    material: float = 0.15,
    severe: float = 0.35,
) -> str:
    if jsd_or_l1 >= severe:
        return "SEVERE_SHIFT"
    if jsd_or_l1 >= material:
        return "MATERIAL_SHIFT"
    return "REP_QUAL_DISTRIBUTION_MATCH"


def review_contract() -> dict[str, Any]:
    return {
        "REVIEW_RULE": REVIEW_RULE,
        "REVIEW_ID": REVIEW_ID,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "QUAL_RESULT_ID": RESULT_ID,
        "expected": {
            "seal_sha256": EXPECTED_SEAL_SHA256,
            "package_sha256": EXPECTED_PACKAGE_SHA256,
            "qual_result_sha256": EXPECTED_QUAL_RESULT_SHA256,
            "n_rows": EXPECTED_N_ROWS,
            "qualification_model_executions": 1,
            "evaluation_spent": "EVALUATION_SPENT",
            "rep_reference_system_macro_f1": REP_REFERENCE_SYSTEM_MACRO_F1,
        },
        "forbidden": [
            "retrain",
            "recalibrate",
            "alter_thresholds",
            "create_new_qualification_surface",
            "inspect_QUAL_001",
            "move_pointers",
            "use_QUAL_002_for_optimization",
            "automatic_architecture_bakeoff",
        ],
        "QUALIFICATION_USED_FOR_OPTIMIZATION": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "RELEASE_ELIGIBLE": False,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "rejected_micro_fixes_default": dict(REJECTED_MICRO_FIXES),
        "primary_diagnoses": list(PRIMARY_DIAGNOSES),
        "v6_dispositions": list(V6_DISPOSITIONS),
        "next_phases": list(NEXT_PHASES),
    }


def derive_system_diagnosis(audit: Mapping[str, Any]) -> dict[str, Any]:
    """Map forensic evidence onto sealed diagnosis / disposition / next phase."""
    rep_audit = dict(audit.get("rep_representativeness") or {})
    geom = dict(audit.get("semantic_geometry") or {})
    axis = dict(audit.get("axis_degradation") or {})
    card = dict(audit.get("cardinality_shift") or {})
    calib = dict(audit.get("calibration_counterfactual") or {})
    task = dict(audit.get("task_signal") or {})
    source = dict(audit.get("source_shift") or {})

    rep_class = rep_audit.get("class") or ""
    none_excluded = bool(rep_audit.get("rep_excluded_zero_label_rows"))
    none_share_qual = float(rep_audit.get("qual_zero_label_share") or 0.0)
    domain_fn_missing_on_rep = bool(
        card.get("rep_domain_plus_function_n") == 0
        and float(card.get("qual_domain_plus_function_n") or 0) > 0
    )
    function_collapsed = bool(axis.get("function_class") in {"SEVERE_DROP", "COLLAPSED"})
    geometry_collapsed = bool(
        geom.get("class") in {"SEMANTIC_ENCODER_DOMAIN_MISMATCH", "GEOMETRY_SHIFTED"}
    )
    calib_class = calib.get("classification") or ""
    source_dom = source.get("class") == "SOURCE_SHIFT_DOMINANT"
    task_insuff = task.get("class") == "TASK_SIGNAL_INSUFFICIENT"

    if none_excluded and none_share_qual >= 0.50 and domain_fn_missing_on_rep:
        diagnosis = "REPRESENTATIVE_VALIDATION_OVERFIT"
        disposition = "V6_REQUIRES_DATA_DISTRIBUTION_REDESIGN"
        next_phase = "REDESIGN_V6_REPRESENTATIVE_VALIDATION_AND_DATA_DIVERSITY"
    elif geometry_collapsed and not none_excluded:
        diagnosis = "SEMANTIC_ENCODER_DOMAIN_MISMATCH"
        disposition = "V6_REQUIRES_REPRESENTATION_REDESIGN"
        next_phase = "REBASE_V6_ON_DIFFERENT_SEMANTIC_REPRESENTATION_FAMILY"
    elif function_collapsed and domain_fn_missing_on_rep and geometry_collapsed:
        diagnosis = "MIXED_V6_SYSTEM_GENERALIZATION_FAILURE"
        disposition = "V6_REQUIRES_DATA_DISTRIBUTION_REDESIGN"
        next_phase = "REDESIGN_V6_REPRESENTATIVE_VALIDATION_AND_DATA_DIVERSITY"
    elif function_collapsed and not none_excluded:
        diagnosis = "AXIS_SPECIFIC_GENERALIZATION_FAILURE"
        disposition = "V6_REQUIRES_REPRESENTATION_REDESIGN"
        next_phase = "TEST_AXIS_SPECIFIC_SEMANTIC_ENCODERS"
    elif calib_class == "CALIBRATION_SHIFT" and not none_excluded:
        diagnosis = "LABEL_PRIOR_CALIBRATION_FAILURE"
        disposition = "V6_RESEARCH_PROTOTYPE_CONTINUE"
        next_phase = "EXPAND_V6_NATURAL_DIVERSITY_BY_FAILURE_STRATA"
    elif task_insuff:
        diagnosis = "TASK_SIGNAL_LIMITATION"
        disposition = "V6_REQUIRES_TASK_REDESIGN"
        next_phase = "REASSESS_HYPERLEX_V6_TASK_DEFINITION"
    elif source_dom:
        diagnosis = "DATA_DIVERSITY_FAILURE"
        disposition = "V6_REQUIRES_DATA_DISTRIBUTION_REDESIGN"
        next_phase = "EXPAND_V6_NATURAL_DIVERSITY_BY_FAILURE_STRATA"
    elif rep_class in {
        "REPRESENTATIVE_VALIDATION_OVERFIT",
        "REPRESENTATIVE_VALIDATION_PARTIAL",
    }:
        diagnosis = "REPRESENTATIVE_VALIDATION_OVERFIT"
        disposition = "V6_REQUIRES_DATA_DISTRIBUTION_REDESIGN"
        next_phase = "REDESIGN_V6_REPRESENTATIVE_VALIDATION_AND_DATA_DIVERSITY"
    else:
        diagnosis = "MIXED_V6_SYSTEM_GENERALIZATION_FAILURE"
        disposition = "V6_RESEARCH_PROTOTYPE_CONTINUE"
        next_phase = "REDESIGN_V6_REPRESENTATIVE_VALIDATION_AND_DATA_DIVERSITY"

    # Preserve secondary contributors without changing primary.
    secondary = []
    if diagnosis != "AXIS_SPECIFIC_GENERALIZATION_FAILURE" and function_collapsed:
        secondary.append("AXIS_SPECIFIC_GENERALIZATION_FAILURE")
    if (
        diagnosis != "MULTI_LABEL_COMPOSITION_GENERALIZATION_FAILURE"
        and domain_fn_missing_on_rep
    ):
        secondary.append("MULTI_LABEL_COMPOSITION_GENERALIZATION_FAILURE")
    if diagnosis != "SEMANTIC_ENCODER_DOMAIN_MISMATCH" and geometry_collapsed:
        secondary.append("SEMANTIC_ENCODER_DOMAIN_MISMATCH")
    if calib_class in {"CALIBRATION_SHIFT", "OPERATING_POINT_CONFLICT"}:
        secondary.append("LABEL_PRIOR_CALIBRATION_FAILURE")

    return {
        "PRIMARY_DIAGNOSIS": diagnosis,
        "SECONDARY_CONTRIBUTORS": secondary,
        "V6_DISPOSITION": disposition,
        "NEXT_ACTION": next_phase,
        "QUALIFICATION_SURFACE_VALIDITY": (
            (audit.get("qual_validity") or {}).get("class") or "HARDER_BUT_VALID"
        ),
        "REP_REPRESENTATIVENESS": rep_class
        or ("REPRESENTATIVE_VALIDATION_OVERFIT" if none_excluded else "REPRESENTATIVE_VALIDATION_PARTIAL"),
        "evidence_flags": {
            "rep_excluded_zero_label_rows": none_excluded,
            "qual_zero_label_share": none_share_qual,
            "rep_missing_domain_plus_function": domain_fn_missing_on_rep,
            "function_collapsed": function_collapsed,
            "geometry_collapsed": geometry_collapsed,
            "calibration_class": calib_class,
            "source_shift_dominant": source_dom,
            "task_insufficient": task_insuff,
        },
    }


def build_system_review_receipt(
    audit: Mapping[str, Any],
    *,
    reviewed_at: str | None = None,
) -> dict[str, Any]:
    clean = jsonable(dict(audit))
    derived = derive_system_diagnosis(clean)
    payload = {
        "BEST_MUTATED": False,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "HUB_PUBLISH_AUTHORIZED": False,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "NEXT_ACTION": derived["NEXT_ACTION"],
        "PRIMARY_DIAGNOSIS": derived["PRIMARY_DIAGNOSIS"],
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "QUALIFICATION_RESULT_SHA256": EXPECTED_QUAL_RESULT_SHA256,
        "QUALIFICATION_SURFACE_VALIDITY": derived["QUALIFICATION_SURFACE_VALIDITY"],
        "QUALIFICATION_USED_FOR_OPTIMIZATION": False,
        "REJECTED_MICRO_FIXES": dict(REJECTED_MICRO_FIXES),
        "RELEASE_ELIGIBLE": False,
        "REP_REPRESENTATIVENESS": derived["REP_REPRESENTATIVENESS"],
        "REVIEW_ID": REVIEW_ID,
        "REVIEW_RULE": REVIEW_RULE,
        "SECONDARY_CONTRIBUTORS": list(derived["SECONDARY_CONTRIBUTORS"]),
        "THRESHOLDS_CHANGED": False,
        "TRAIN": False,
        "V6_DISPOSITION": derived["V6_DISPOSITION"],
        "audit": clean,
        "derived": derived,
        "reviewed_at": reviewed_at or utc_now_iso(),
        "schema": SCHEMA,
    }
    payload["SYSTEM_REVIEW_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {k: v for k, v in payload.items() if k != "SYSTEM_REVIEW_RECEIPT_SHA256"}
        )
    )
    return payload


__all__ = [
    "DROP_BANDS",
    "EXPERIMENT_ID",
    "EXPECTED_QUAL_RESULT_SHA256",
    "NEXT_PHASES",
    "PRIMARY_DIAGNOSES",
    "REJECTED_MICRO_FIXES",
    "REVIEW_ID",
    "REVIEW_RULE",
    "V6_DISPOSITIONS",
    "build_system_review_receipt",
    "classify_drop",
    "classify_shift",
    "derive_system_diagnosis",
    "jsonable",
    "review_contract",
    "utc_now_iso",
]
