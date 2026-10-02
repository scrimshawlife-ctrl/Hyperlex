"""REVIEW_V6_QUALIFICATION_003_FAILURE — contracts.

Read-only forensic review after HYPERLEX_V6_QUALIFICATION_003 FAIL.
Focus: positive-semantic / FUNCTION generalization. NONE gate provisionally
frozen unless evidence shows it dominates function loss.
"""

from __future__ import annotations

from typing import Any, Mapping

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
from .classification_v6_operating_pipeline_harden import (
    PACKAGE_ID,
    WITNESS_REP_POSITIVE_ONLY,
    WITNESS_REP_SYSTEM_MACRO_F1,
    WITNESS_REP_ZERO_EXACT,
    WITNESS_REP_ZERO_FP,
)
from .classification_v6_qualification_execute_003 import (
    EXPECTED_N_ROWS,
    EXPECTED_PACKAGE_SHA256,
    EXPECTED_SEAL_SHA256,
    QUALIFICATION_ID,
    RESULT_ID,
)

REVIEW_RULE = "REVIEW_V6_QUALIFICATION_003_FAILURE"
REVIEW_ID = "HYPERLEX_V6_QUALIFICATION_003_FAILURE_REVIEW_001"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-QUALIFICATION-003-FAILURE-REVIEW-001"
SCHEMA = "hyperlex.classification.v6.qualification_003_failure_review.v1"

EXPECTED_QUAL_RESULT_SHA256 = (
    "b560dac2a8f80f45c6213dcd2ba25acdb2e0b7dde786da3ee0a5d6e3231ae724"
)

PRIMARY_DIAGNOSES = (
    "POSITIVE_GATE_GENERALIZATION_FAILURE",
    "FUNCTION_HEAD_GENERALIZATION_FAILURE",
    "FUNCTION_DATA_DIVERSITY_FAILURE",
    "POSITIVE_REPRESENTATIVE_VALIDATION_OVERFIT",
    "FUNCTION_TASK_SIGNAL_LIMITATION",
    "MIXED_POSITIVE_SEMANTIC_GENERALIZATION_FAILURE",
)

NONE_GATE_STATUSES = (
    "NONE_GATE_FROZEN_RETAIN",
    "NONE_GATE_REOPEN_REQUIRED",
)

POSITIVE_REP_CLASSES = (
    "POSITIVE_REPRESENTATIVENESS_VALID",
    "POSITIVE_REPRESENTATIVENESS_PARTIAL",
    "POSITIVE_REPRESENTATIVENESS_OVERFIT",
)

FUNCTION_FAILURE_MODES = (
    "GATE_INDUCED",
    "HEAD_GENERALIZATION",
    "FUNCTION_DATA_DIVERSITY",
    "FUNCTION_DEFINITION / TASK_SIGNAL",
    "MIXED",
)

REPRESENTATION_FINDINGS = (
    "HEAD_GENERALIZATION_FAILURE",
    "REPRESENTATION_GENERALIZATION_FAILURE",
    "MIXED_GEOMETRY_AND_HEAD",
    "INCONCLUSIVE_WITHOUT_GEOMETRY",
)

LEARNABILITY = (
    "HUMAN_STABLE_MODEL_LEARNABLE",
    "HUMAN_STABLE_BUT_STATISTICALLY_WEAK",
    "CONTEXT_DEPENDENT_IN_OPERATING_TEXT",
    "UNDERREPRESENTED",
)

NEXT_PHASES = (
    "HARDEN_V6_POSITIVE_ADMISSION_AND_FUNCTION_GENERALIZATION",
    "EXPAND_V6_FUNCTION_DIVERSITY_AND_POSITIVE_REPRESENTATION",
    "REDESIGN_V6_FUNCTION_PREDICTION",
    "REASSESS_V6_FUNCTION_TASK_DEFINITION",
)

REJECTED_MICRO_FIXES = {
    "retune_ANY_LABEL_threshold": False,
    "modify_NONE_rejection": False,
    "retrain_encoder": False,
    "change_ontology": False,
    "another_QUAL_surface_now": False,
    "use_QUAL_003_for_optimization": False,
    "architecture_bakeoff": False,
    "seed_sweep": False,
}


def _hash(payload: Any) -> str:
    return sha256_text(canonical_json(payload))


def review_contract() -> dict[str, Any]:
    return {
        "REVIEW_RULE": REVIEW_RULE,
        "REVIEW_ID": REVIEW_ID,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "QUAL_RESULT_ID": RESULT_ID,
        "PACKAGE_ID": PACKAGE_ID,
        "expected": {
            "seal_sha256": EXPECTED_SEAL_SHA256,
            "package_sha256": EXPECTED_PACKAGE_SHA256,
            "qual_result_sha256": EXPECTED_QUAL_RESULT_SHA256,
            "n_rows": EXPECTED_N_ROWS,
            "qualification_model_executions": 1,
            "evaluation_spent": "EVALUATION_SPENT",
            "rep_system_macro_f1": WITNESS_REP_SYSTEM_MACRO_F1,
            "rep_zero_fp": WITNESS_REP_ZERO_FP,
            "rep_zero_exact": WITNESS_REP_ZERO_EXACT,
            "rep_positive_only": WITNESS_REP_POSITIVE_ONLY,
        },
        "forbidden": [
            "retune_ANY_LABEL_threshold",
            "modify_NONE_rejection",
            "retrain",
            "change_ontology",
            "create_new_qualification_surface",
            "use_QUAL_003_for_optimization",
            "architecture_bakeoff",
            "move_pointers",
        ],
        "QUALIFICATION_USED_FOR_OPTIMIZATION": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "RELEASE_ELIGIBLE": False,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "rejected_micro_fixes_default": dict(REJECTED_MICRO_FIXES),
        "primary_diagnoses": list(PRIMARY_DIAGNOSES),
        "next_phases": list(NEXT_PHASES),
    }


def classify_function_failure_mode(audit: Mapping[str, Any]) -> str:
    gate = dict(audit.get("positive_false_reject") or {})
    fun = dict(audit.get("function_failure") or {})
    gate_share_fun = float(fun.get("gate_reject_rate_on_function_gold") or 0.0)
    admitted_recall = float(fun.get("admitted_mean_recall") or 0.0)
    support_ratio = float(fun.get("qual_to_rep_support_ratio") or 1.0)
    length_shift = bool(fun.get("length_shift_severe"))
    wiki_none_contam = float(fun.get("qual_function_wiki_none_share") or 0.0)

    diversity = support_ratio < 0.35 or length_shift or wiki_none_contam >= 0.25
    gate_induced = gate_share_fun >= 0.45 and admitted_recall >= 0.25
    head_fail = admitted_recall < 0.15

    modes = []
    if gate_induced:
        modes.append("GATE_INDUCED")
    if head_fail:
        modes.append("HEAD_GENERALIZATION")
    if diversity:
        modes.append("FUNCTION_DATA_DIVERSITY")
    if len(modes) >= 2:
        return "MIXED"
    if modes:
        return modes[0]
    if float(gate.get("gate_reject_rate_on_positives") or 0.0) >= 0.40:
        return "GATE_INDUCED"
    return "MIXED"


def derive_diagnosis(audit: Mapping[str, Any]) -> dict[str, Any]:
    """Map forensic evidence to sealed diagnosis / NONE status / next phase."""
    gate = dict(audit.get("positive_false_reject") or {})
    fun = dict(audit.get("function_failure") or {})
    pos_rep = dict(audit.get("positive_representativeness") or {})
    geom = dict(audit.get("representation_vs_head") or {})
    learn = dict(audit.get("function_learnability") or {})
    none = dict(audit.get("none_gate") or {})

    gate_rate = float(gate.get("gate_reject_rate_on_positives") or 0.0)
    final_empty_rate = float(gate.get("final_empty_rate_on_positives") or 0.0)
    post_admit_empty_share = float(
        gate.get("post_admission_empty_share_of_final_empty") or 0.0
    )
    fun_mode = fun.get("mode") or classify_function_failure_mode(audit)
    fun_gate_rate = float(fun.get("gate_reject_rate_on_function_gold") or 0.0)
    admitted_recall = float(fun.get("admitted_mean_recall") or 0.0)
    support_ratio = float(fun.get("qual_to_rep_support_ratio") or 1.0)
    pos_rep_class = pos_rep.get("class") or "POSITIVE_REPRESENTATIVENESS_PARTIAL"
    geom_class = geom.get("class") or "INCONCLUSIVE_WITHOUT_GEOMETRY"
    learn_class = learn.get("class") or "UNDERREPRESENTED"

    none_pass = bool(none.get("operating_gates_pass"))
    none_dominates_function = fun_gate_rate >= 0.60 and admitted_recall >= 0.20

    # Primary diagnosis priority
    if (
        gate_rate >= 0.45
        and post_admit_empty_share < 0.25
        and fun_mode == "GATE_INDUCED"
    ):
        diagnosis = "POSITIVE_GATE_GENERALIZATION_FAILURE"
        next_phase = "HARDEN_V6_POSITIVE_ADMISSION_AND_FUNCTION_GENERALIZATION"
    elif (
        fun_mode == "FUNCTION_DATA_DIVERSITY"
        or (
            support_ratio < 0.35
            and pos_rep_class
            in {
                "POSITIVE_REPRESENTATIVENESS_PARTIAL",
                "POSITIVE_REPRESENTATIVENESS_OVERFIT",
            }
        )
    ) and admitted_recall < 0.20:
        diagnosis = "MIXED_POSITIVE_SEMANTIC_GENERALIZATION_FAILURE"
        # Diversity + head collapse → expand positive/function representation first
        next_phase = "EXPAND_V6_FUNCTION_DIVERSITY_AND_POSITIVE_REPRESENTATION"
    elif fun_mode == "HEAD_GENERALIZATION" and geom_class == "HEAD_GENERALIZATION_FAILURE":
        diagnosis = "FUNCTION_HEAD_GENERALIZATION_FAILURE"
        next_phase = "HARDEN_V6_POSITIVE_ADMISSION_AND_FUNCTION_GENERALIZATION"
    elif pos_rep_class == "POSITIVE_REPRESENTATIVENESS_OVERFIT":
        diagnosis = "POSITIVE_REPRESENTATIVE_VALIDATION_OVERFIT"
        next_phase = "EXPAND_V6_FUNCTION_DIVERSITY_AND_POSITIVE_REPRESENTATION"
    elif learn_class in {
        "CONTEXT_DEPENDENT_IN_OPERATING_TEXT",
        "HUMAN_STABLE_BUT_STATISTICALLY_WEAK",
    } and support_ratio >= 0.5:
        diagnosis = "FUNCTION_TASK_SIGNAL_LIMITATION"
        next_phase = "REASSESS_V6_FUNCTION_TASK_DEFINITION"
    elif fun_mode == "FUNCTION_DATA_DIVERSITY":
        diagnosis = "FUNCTION_DATA_DIVERSITY_FAILURE"
        next_phase = "EXPAND_V6_FUNCTION_DIVERSITY_AND_POSITIVE_REPRESENTATION"
    else:
        diagnosis = "MIXED_POSITIVE_SEMANTIC_GENERALIZATION_FAILURE"
        next_phase = "EXPAND_V6_FUNCTION_DIVERSITY_AND_POSITIVE_REPRESENTATION"

    # Override: clear mixed with both gate and head+diversity
    if (
        fun_gate_rate >= 0.40
        and admitted_recall < 0.15
        and support_ratio < 0.40
    ):
        diagnosis = "MIXED_POSITIVE_SEMANTIC_GENERALIZATION_FAILURE"
        next_phase = "EXPAND_V6_FUNCTION_DIVERSITY_AND_POSITIVE_REPRESENTATION"

    none_status = (
        "NONE_GATE_REOPEN_REQUIRED"
        if none_dominates_function and not none_pass
        else "NONE_GATE_FROZEN_RETAIN"
    )
    # Even if function gate-reject high, keep frozen if operating zero-label gates pass
    # and post-admission head failure is material.
    if none_pass and post_admit_empty_share >= 0.25:
        none_status = "NONE_GATE_FROZEN_RETAIN"

    return {
        "PRIMARY_DIAGNOSIS": diagnosis,
        "FUNCTION_FAILURE_MODE": fun_mode,
        "POSITIVE_REPRESENTATIVENESS": pos_rep_class,
        "REPRESENTATION_VS_HEAD": geom_class,
        "FUNCTION_LEARNABILITY": learn_class,
        "NONE_GATE_STATUS": none_status,
        "NEXT_ACTION": next_phase,
        "evidence_summary": {
            "gate_reject_rate_on_positives": gate_rate,
            "final_empty_rate_on_positives": final_empty_rate,
            "post_admission_empty_share_of_final_empty": post_admit_empty_share,
            "function_gate_reject_rate": fun_gate_rate,
            "function_admitted_mean_recall": admitted_recall,
            "qual_to_rep_function_support_ratio": support_ratio,
        },
    }


def build_review_receipt(
    audit: Mapping[str, Any], *, reviewed_at: str
) -> dict[str, Any]:
    derived = derive_diagnosis(audit)
    body = {
        "REVIEW_RULE": REVIEW_RULE,
        "REVIEW_ID": REVIEW_ID,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "QUAL_RESULT_ID": RESULT_ID,
        "QUAL_RESULT_SHA256": EXPECTED_QUAL_RESULT_SHA256,
        "PACKAGE_SHA256": EXPECTED_PACKAGE_SHA256,
        "QUAL_SEAL_SHA256": EXPECTED_SEAL_SHA256,
        "PRIMARY_DIAGNOSIS": derived["PRIMARY_DIAGNOSIS"],
        "FUNCTION_FAILURE_MODE": derived["FUNCTION_FAILURE_MODE"],
        "POSITIVE_REPRESENTATIVENESS": derived["POSITIVE_REPRESENTATIVENESS"],
        "REPRESENTATION_VS_HEAD": derived["REPRESENTATION_VS_HEAD"],
        "FUNCTION_LEARNABILITY": derived["FUNCTION_LEARNABILITY"],
        "NONE_GATE_STATUS": derived["NONE_GATE_STATUS"],
        "NEXT_ACTION": derived["NEXT_ACTION"],
        "evidence_summary": derived["evidence_summary"],
        "audit": dict(audit),
        "REJECTED_MICRO_FIXES": dict(REJECTED_MICRO_FIXES),
        "QUALIFICATION_USED_FOR_OPTIMIZATION": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "RELEASE_ELIGIBLE": False,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "V6_OPERATING_PIPELINE_CANDIDATE_MUTATED": False,
        "reviewed_at": reviewed_at,
    }
    body["SYSTEM_REVIEW_RECEIPT_SHA256"] = _hash(
        {k: v for k, v in body.items() if k != "SYSTEM_REVIEW_RECEIPT_SHA256"}
    )
    return body


__all__ = [
    "EXPECTED_QUAL_RESULT_SHA256",
    "EXPERIMENT_ID",
    "FUNCTION_FAILURE_MODES",
    "LEARNABILITY",
    "NEXT_PHASES",
    "NONE_GATE_STATUSES",
    "POSITIVE_REP_CLASSES",
    "PRIMARY_DIAGNOSES",
    "REJECTED_MICRO_FIXES",
    "REPRESENTATION_FINDINGS",
    "REVIEW_ID",
    "REVIEW_RULE",
    "build_review_receipt",
    "classify_function_failure_mode",
    "derive_diagnosis",
    "review_contract",
]
