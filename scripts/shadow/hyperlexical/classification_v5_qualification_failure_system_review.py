"""REVIEW_V5_QUALIFICATION_FAILURE_AT_SYSTEM_LEVEL — contracts and settlement.

Read-only system diagnosis after HYPERLEX_V5_PIPELINE_QUALIFICATION_001 FAIL.
Does not train, retune, rebuild index, move BEST, or optimize on qualification.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from .classification_v5_pipeline_qualification import (
    DEPENDENCY_MANIFEST_SHA256_PIN,
    QUALIFICATION_ID,
    SEAL_PACKAGE_RECEIPT_SHA256_PIN,
)
from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import (
    MODEL_WIDE_BEST_SHA256,
    STAGE_A_BEST_SHA256,
)
from .classification_v5_stage_b import FROZEN_INDEX_SHA256

REVIEW_RULE = "REVIEW_V5_QUALIFICATION_FAILURE_AT_SYSTEM_LEVEL"
REVIEW_ID = "HYPERLEX_V5_QUALIFICATION_FAILURE_SYSTEM_REVIEW_001"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V5-QUALIFICATION-FAILURE-SYSTEM-REVIEW-001"
SCHEMA = "hyperlex.classification.v5.qualification_failure_system_review.v1"

SYSTEM_DIAGNOSIS = "MIXED_SYSTEM_GENERALIZATION_FAILURE"
V5_DISPOSITION = "V5_RESEARCH_PROTOTYPE"
PRIMARY_REMEDIATION_PHASE = "BUILD_REPRESENTATIVE_V6_DATA_FOUNDATION"
NEXT_ACTION = "BUILD_REPRESENTATIVE_V6_DATA_FOUNDATION"
QUALIFICATION_SURFACE_VALIDITY = "QUALIFICATION_SURFACE_HARD_BUT_VALID"

REJECTED_MICRO_FIXES = {
    "more_stage_a_threshold_tuning": False,
    "another_stage_a_matched_surface": False,
    "another_stage_b_floor_tune": False,
    "simply_enlarging_existing_index": False,
    "another_reserve": False,
    "another_local_loss_change": False,
}

PRESERVED_TRUTHS = [
    "gold_identifiability_mattered",
    "serialization_defect_was_real",
    "factorized_checkpoint_is_loadable",
    "SHORT_ATOM_NONE_historical_failure_was_repaired",
    "Stage_B_works_on_its_original_V1R2_validation_surface",
]


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def derive_system_diagnosis(audit: Mapping[str, Any]) -> dict[str, Any]:
    """Map audit evidence onto the sealed system diagnosis enums."""
    stage_a = dict(audit.get("stage_a") or {})
    stage_b = dict(audit.get("stage_b_independent") or {})
    dist = dict(audit.get("distribution") or {})
    calib = dict(audit.get("stage_a_calibration") or {})
    repr_info = dict(audit.get("representation") or {})

    a_collapse = (
        float((stage_a.get("qualification") or {}).get("false_entry") or 0) >= 0.15
        and float((stage_a.get("qualification") or {}).get("present_recall") or 1) <= 0.75
    )
    b_indep = bool(stage_b.get("independent_generalization_failure"))
    shift = (
        dist.get("stage_a_shift_class") == "MATERIAL_DISTRIBUTION_SHIFT"
        and dist.get("stage_b_shift_class") == "MATERIAL_DISTRIBUTION_SHIFT"
    )
    structural = calib.get("classification") == "STRUCTURAL_OVERLAP"
    no_rescue = not bool(calib.get("any_threshold_region_rescues_primary_gates"))

    if a_collapse and b_indep and shift:
        diagnosis = "MIXED_SYSTEM_GENERALIZATION_FAILURE"
    elif a_collapse and not b_indep:
        diagnosis = "STAGE_A_OVERFIT_GENERALIZATION_FAILURE"
    elif b_indep and not a_collapse:
        diagnosis = "STAGE_B_INDEX_GENERALIZATION_FAILURE"
    elif shift and not (a_collapse and b_indep):
        diagnosis = "QUALIFICATION_DISTRIBUTION_MISMATCH"
    else:
        diagnosis = "PIPELINE_COMPOSITION_FAILURE"

    disposition = "V5_RESEARCH_PROTOTYPE"
    if diagnosis == "MIXED_SYSTEM_GENERALIZATION_FAILURE" and structural and no_rescue:
        remediation = "BUILD_REPRESENTATIVE_V6_DATA_FOUNDATION"
    elif diagnosis == "ONTOLOGY_GENERALIZATION_FAILURE":
        remediation = "REVISE_FAMILY_ONTOLOGY"
    elif diagnosis == "REPRESENTATION_GENERALIZATION_FAILURE":
        remediation = "REVISIT_BASE_ENCODER_OR_REPRESENTATION"
    else:
        remediation = "BUILD_REPRESENTATIVE_V6_DATA_FOUNDATION"

    return {
        "SYSTEM_DIAGNOSIS": diagnosis,
        "V5_DISPOSITION": disposition,
        "PRIMARY_REMEDIATION_PHASE": remediation,
        "QUALIFICATION_SURFACE_VALIDITY": (
            (audit.get("surface_validity") or {}).get("disposition")
            or QUALIFICATION_SURFACE_VALIDITY
        ),
        "representation_class": repr_info.get("representation_class"),
        "ontology_separability": audit.get("ontology_separability")
        or repr_info.get("ontology_separability"),
        "evidence_flags": {
            "stage_a_collapse": a_collapse,
            "stage_b_independent_failure": b_indep,
            "material_distribution_shift": shift,
            "structural_overlap": structural,
            "no_threshold_rescue": no_rescue,
        },
    }


def build_system_review_receipt(
    audit: Mapping[str, Any],
    *,
    reviewed_at: str | None = None,
) -> dict[str, Any]:
    derived = derive_system_diagnosis(audit)
    payload = {
        "BEST_MUTATED": False,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "HUB_PUBLISH_AUTHORIZED": False,
        "INDEX_REBUILT": False,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "NEXT_ACTION": derived["PRIMARY_REMEDIATION_PHASE"],
        "PIPELINE_DEPENDENCY_MANIFEST_SHA256": DEPENDENCY_MANIFEST_SHA256_PIN,
        "PRIMARY_REMEDIATION_PHASE": derived["PRIMARY_REMEDIATION_PHASE"],
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "QUALIFICATION_SURFACE_VALIDITY": derived["QUALIFICATION_SURFACE_VALIDITY"],
        "QUALIFICATION_USED_FOR_OPTIMIZATION": False,
        "REJECTED_MICRO_FIXES": dict(REJECTED_MICRO_FIXES),
        "RELEASE_ELIGIBLE": False,
        "REVIEW_ID": REVIEW_ID,
        "REVIEW_RULE": REVIEW_RULE,
        "SEAL_PACKAGE_RECEIPT_SHA256": SEAL_PACKAGE_RECEIPT_SHA256_PIN,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "STAGE_B_INDEX": FROZEN_INDEX_SHA256,
        "SYSTEM_DIAGNOSIS": derived["SYSTEM_DIAGNOSIS"],
        "THRESHOLDS_CHANGED": False,
        "TRAIN": False,
        "V5_DISPOSITION": derived["V5_DISPOSITION"],
        "audit": dict(audit),
        "derived": derived,
        "preserved_truths": list(PRESERVED_TRUTHS),
        "reviewed_at": reviewed_at or utc_now_iso(),
        "schema": SCHEMA,
    }
    payload["SYSTEM_REVIEW_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {k: v for k, v in payload.items() if k != "SYSTEM_REVIEW_RECEIPT_SHA256"}
        )
    )
    return payload
