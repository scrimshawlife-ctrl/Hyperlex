"""REDESIGN_V6_REPRESENTATIVE_VALIDATION_AND_DATA_DIVERSITY — contracts.

Rebuild TRAIN/DEV/REP V2 so development evaluation includes NONE traffic
and co-label structure. Hardened V6 package stays frozen. QUAL-002 is
historical aggregate comparison only.
"""

from __future__ import annotations

from typing import Any, Mapping

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
from .classification_v6_data_foundation import OPERATING_DISTRIBUTION_ID
from .classification_v6_qualification_execute_002 import (
    EXPECTED_PACKAGE_SHA256,
    EXPECTED_SEAL_SHA256,
    QUALIFICATION_ID,
    REP_REFERENCE_SYSTEM_MACRO_F1,
)
from .classification_v6_qualification_failure_system_review import (
    EXPECTED_QUAL_RESULT_SHA256,
)
from .classification_v6_semantic_pipeline_harden import PACKAGE_ID

PHASE_RULE = "REDESIGN_V6_REPRESENTATIVE_VALIDATION_AND_DATA_DIVERSITY"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-REPRESENTATIVE-VALIDATION-REDESIGN-001"
SCHEMA = "hyperlex.classification.v6.representative_validation_redesign.v1"

TRAIN_V2_ID = "HYPERLEX_V6_TRAIN_V2"
DEV_V2_ID = "HYPERLEX_V6_DEV_SELECTION_V2"
REP_V2_ID = "HYPERLEX_V6_REPRESENTATIVE_VALIDATION_V2"

# Broad operating ranges inspired by QUAL aggregate findings — not exact copy.
REP_V2_ZERO_LABEL_SHARE_RANGE = (0.55, 0.75)
REP_V2_NO_EVIDENCE_SHARE_RANGE = (0.45, 0.70)
REP_V2_MIN_N = 900
DEV_V2_MIN_N = 400
TRAIN_V2_MIN_N = 2000

FORBIDDEN_FILTERS = (
    "EVIDENCE_PRESENT_required",
    "positive_semantic_labels_required",
    "usable()",
)

REMAINING_FAILURE_CLASSES = (
    "NONE_REJECTION_FAILURE",
    "FUNCTION_GENERALIZATION_FAILURE",
    "CO_LABEL_COMPOSITION_FAILURE",
    "POSITIVE_SEMANTIC_DISCRIMINATION_FAILURE",
    "MIXED_MODEL_FAILURE",
)


def redesign_contract() -> dict[str, Any]:
    return {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "surface_ids": {
            "TRAIN": TRAIN_V2_ID,
            "DEV_SELECTION": DEV_V2_ID,
            "REPRESENTATIVE_VALIDATION": REP_V2_ID,
        },
        "OPERATING_DISTRIBUTION_ID": OPERATING_DISTRIBUTION_ID,
        "frozen_package": {
            "PACKAGE_ID": PACKAGE_ID,
            "PACKAGE_SHA256": EXPECTED_PACKAGE_SHA256,
            "retrain": False,
            "retune": False,
            "ontology_changed": False,
        },
        "historical_qual": {
            "QUALIFICATION_ID": QUALIFICATION_ID,
            "seal_sha256": EXPECTED_SEAL_SHA256,
            "result_sha256": EXPECTED_QUAL_RESULT_SHA256,
            "role": "AGGREGATE_HISTORICAL_COMPARISON_ONLY",
            "row_reuse_forbidden": True,
            "new_qualification_surface": False,
        },
        "forbidden_filters": list(FORBIDDEN_FILTERS),
        "rep_v2_targets": {
            "zero_label_share": list(REP_V2_ZERO_LABEL_SHARE_RANGE),
            "no_evidence_share": list(REP_V2_NO_EVIDENCE_SHARE_RANGE),
            "min_n": REP_V2_MIN_N,
            "must_include": [
                "NO_EVIDENCE_zero_label_traffic",
                "positive_traffic",
                "function_labels",
                "multi_label_compositions",
                "domain_plus_function_when_naturally_available",
                "source_style_diversity",
                "length_diversity",
            ],
        },
        "success_criterion": (
            "Representativeness repaired if frozen-model REP_V2 exposes the "
            "QUAL-002 failure shape (NONE overprediction + function weakness). "
            "Not success to recover old usable-REP ~0.432."
        ),
        "old_usable_rep_macro_f1": REP_REFERENCE_SYSTEM_MACRO_F1,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "RELEASE_ELIGIBLE": False,
    }


def in_range(value: float, lo: float, hi: float) -> bool:
    return float(lo) <= float(value) <= float(hi)


def classify_remaining_model_failure(replay: Mapping[str, Any]) -> dict[str, Any]:
    """Classify residual model failure after representativeness is repaired."""
    zero_fp = float(replay.get("zero_label_false_positive_rate") or 0.0)
    fn_macro = float(replay.get("FUNCTION_macro_f1") or 0.0)
    sys_macro = float(replay.get("system_macro_f1") or 0.0)
    co_label = float(
        (replay.get("co_label_performance") or {}).get("domain_plus_function_system_macro")
        or 0.0
    )
    pos_macro = float(replay.get("positive_only_system_macro_f1") or 0.0)

    none_fail = zero_fp >= 0.40
    function_fail = fn_macro < 0.15
    co_fail = (
        replay.get("n_domain_plus_function", 0) >= 5 and co_label < 0.15
    )
    pos_fail = pos_macro < 0.25

    flags = {
        "NONE_REJECTION_FAILURE": none_fail,
        "FUNCTION_GENERALIZATION_FAILURE": function_fail,
        "CO_LABEL_COMPOSITION_FAILURE": co_fail,
        "POSITIVE_SEMANTIC_DISCRIMINATION_FAILURE": pos_fail,
    }
    active = [k for k, v in flags.items() if v]
    if len(active) >= 2:
        primary = "MIXED_MODEL_FAILURE"
    elif active:
        primary = active[0]
    elif sys_macro < 0.30:
        primary = "MIXED_MODEL_FAILURE"
    else:
        primary = "POSITIVE_SEMANTIC_DISCRIMINATION_FAILURE"

    return {
        "REMAINING_MODEL_FAILURE": primary,
        "flags": flags,
        "active": active,
        "evidence": {
            "zero_label_false_positive_rate": zero_fp,
            "FUNCTION_macro_f1": fn_macro,
            "system_macro_f1": sys_macro,
            "positive_only_system_macro_f1": pos_macro,
            "domain_plus_function_system_macro": co_label,
        },
    }


def classify_representativeness_repair(
    *,
    rep_audit_pass: bool,
    replay: Mapping[str, Any],
    qual_aggregate: Mapping[str, Any],
) -> dict[str, Any]:
    """Success = REP_V2 exposes QUAL-like failure shape, not high score recovery."""
    zero_fp = float(replay.get("zero_label_false_positive_rate") or 0.0)
    fn = float(replay.get("FUNCTION_macro_f1") or 0.0)
    sys_m = float(replay.get("system_macro_f1") or 0.0)
    qual_sys = float(qual_aggregate.get("system_macro_f1") or 0.0)
    qual_fn = float(qual_aggregate.get("FUNCTION_macro_f1") or 0.0)
    qual_zero_fp = float(qual_aggregate.get("zero_label_false_positive_rate") or 0.0)

    same_shape = (
        sys_m < 0.30
        and fn < 0.20
        and zero_fp >= 0.35
        and abs(sys_m - qual_sys) < 0.20
    )
    repaired = bool(rep_audit_pass and same_shape)
    # Explicitly reject "recovered old REP" as success.
    recovered_old = sys_m >= 0.40
    return {
        "REPRESENTATIVENESS_REPAIRED": repaired,
        "same_broad_failure_shape_as_QUAL_002": same_shape,
        "recovered_old_usable_rep_score": recovered_old,
        "success_definition": "expose_real_weaknesses_not_recover_0.432",
        "comparison": {
            "REP_V2_system_macro_f1": sys_m,
            "QUAL_system_macro_f1": qual_sys,
            "REP_V2_FUNCTION_macro_f1": fn,
            "QUAL_FUNCTION_macro_f1": qual_fn,
            "REP_V2_zero_fp_rate": zero_fp,
            "QUAL_zero_fp_rate": qual_zero_fp,
        },
    }


def decide_next_action(
    *,
    representativeness_repaired: bool,
    remaining_failure: str,
) -> str:
    if not representativeness_repaired:
        return "REPAIR_V6_REPRESENTATIVE_VALIDATION_V2_INTEGRITY"
    if remaining_failure == "NONE_REJECTION_FAILURE":
        return "HARDEN_V6_NONE_REJECTION_UNDER_FROZEN_ENCODER"
    if remaining_failure == "FUNCTION_GENERALIZATION_FAILURE":
        return "TEST_AXIS_SPECIFIC_SEMANTIC_ENCODERS"
    if remaining_failure == "CO_LABEL_COMPOSITION_FAILURE":
        return "EXPAND_V6_NATURAL_CO_LABEL_DIVERSITY"
    if remaining_failure == "POSITIVE_SEMANTIC_DISCRIMINATION_FAILURE":
        return "REBASE_V6_ON_DIFFERENT_SEMANTIC_REPRESENTATION_FAMILY"
    return "ADDRESS_V6_MIXED_MODEL_FAILURE_UNDER_REPRESENTATIVE_REP_V2"


def build_redesign_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    body = dict(payload)
    body["MODEL_WIDE_BEST"] = MODEL_WIDE_BEST_SHA256
    body["MODEL_WIDE_BEST_MUTATED"] = False
    body["HUB_PUBLISH_AUTHORIZED"] = False
    body["RELEASE_ELIGIBLE"] = False
    body["TRAIN_REPLAY_ONLY"] = True
    body["QUAL_002_ROWS_USED_FOR_OPTIMIZATION"] = False
    body["schema"] = SCHEMA
    body["V6_REPRESENTATIVE_VALIDATION_REDESIGN_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in body.items()
                if k != "V6_REPRESENTATIVE_VALIDATION_REDESIGN_RECEIPT_SHA256"
            }
        )
    )
    return body


__all__ = [
    "DEV_V2_ID",
    "DEV_V2_MIN_N",
    "EXPERIMENT_ID",
    "FORBIDDEN_FILTERS",
    "PHASE_RULE",
    "REP_V2_ID",
    "REP_V2_MIN_N",
    "REP_V2_NO_EVIDENCE_SHARE_RANGE",
    "REP_V2_ZERO_LABEL_SHARE_RANGE",
    "REMAINING_FAILURE_CLASSES",
    "TRAIN_V2_ID",
    "TRAIN_V2_MIN_N",
    "build_redesign_receipt",
    "classify_remaining_model_failure",
    "classify_representativeness_repair",
    "decide_next_action",
    "in_range",
    "redesign_contract",
]
