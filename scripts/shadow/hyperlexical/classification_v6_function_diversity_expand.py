"""EXPAND_V6_FUNCTION_DIVERSITY_AND_POSITIVE_REPRESENTATION — contracts.

Rebuild TRAIN/DEV/REP V3 with broader natural positive/FUNCTION diversity.
Encoder, ANY_LABEL gate, axis-head architecture, ontology, and thresholds
stay frozen. QUAL-003 remains EVALUATION_SPENT / unused for optimization.
"""

from __future__ import annotations

from typing import Any, Mapping

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
from .classification_v6_operating_pipeline_harden import (
    PACKAGE_ID as OPERATING_PACKAGE_ID,
    WITNESS_GATE_THRESHOLD,
    WITNESS_REP_POSITIVE_ONLY,
    WITNESS_REP_SYSTEM_MACRO_F1,
    WITNESS_REP_ZERO_EXACT,
    WITNESS_REP_ZERO_FP,
)
from .classification_v6_qualification_003_failure_review import (
    EXPECTED_QUAL_RESULT_SHA256,
)
from .classification_v6_qualification_execute_003 import (
    EXPECTED_PACKAGE_SHA256,
    EXPECTED_SEAL_SHA256,
    QUALIFICATION_ID,
)
from .classification_v6_representative_validation_redesign import (
    DEV_V2_ID,
    REP_V2_ID,
    TRAIN_V2_ID,
)
from .classification_v6_semantic_pipeline_harden import (
    BAKEOFF_THRESHOLDS,
    SELECTED_ENCODER_MODEL_ID,
    SELECTED_ENCODER_REVISION,
)

PHASE_RULE = "EXPAND_V6_FUNCTION_DIVERSITY_AND_POSITIVE_REPRESENTATION"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-FUNCTION-DIVERSITY-EXPAND-001"
SCHEMA = "hyperlex.classification.v6.function_diversity_expand.v1"
REVIEW_RECEIPT_SHA256 = (
    "cf36ef3acb22094bec39bf046083aeb0a9e5efed880be0e9a95fff10abc2b274"
)

TRAIN_V3_ID = "HYPERLEX_V6_TRAIN_V3"
DEV_V3_ID = "HYPERLEX_V6_DEV_SELECTION_V3"
REP_V3_ID = "HYPERLEX_V6_REPRESENTATIVE_VALIDATION_V3"

FUNCTION_VOCAB = (
    "function.relational_intimacy",
    "function.conflictive_force",
    "function.evaluative_stance",
    "function.memetic_form",
)

# Diversity targets for positive/function traffic (not QUAL row targeting).
REP_V3_ZERO_LABEL_SHARE_RANGE = (0.55, 0.75)
REP_V3_MIN_FUNCTION_N = 120
REP_V3_MIN_FUNCTION_NON_WIKT_SHARE = 0.20
REP_V3_MIN_FUNCTION_MEDIUM_LONG_SHARE = 0.50
REP_V3_MIN_DOMAIN_FUNCTION_PAIRS = 8
PER_FUNCTION_MIN_REP = 12
PER_FUNCTION_MIN_TRAIN = 40

OUTCOMES = (
    "V6_FUNCTION_DIVERSITY_ADVANCE",
    "V6_FUNCTION_DIVERSITY_PARTIAL",
    "V6_FUNCTION_DIVERSITY_NO_ADVANCE",
)

NEXT_ACTIONS = (
    "HARDEN_V6_POSITIVE_SEMANTIC_GENERALIZATION",
    "REDESIGN_V6_FUNCTION_PREDICTION",
    "CONTINUE_V6_FUNCTION_DATA_ACQUISITION",
)

# NONE preservation vs operating witness (frozen gate).
NONE_ZERO_FP_MAX = 0.35
NONE_ZERO_EXACT_MIN = 0.50
NONE_REGRESSION_FP_DELTA_MAX = 0.08  # vs witness 0.088 on new REP zero-label


def _hash(payload: Any) -> str:
    return sha256_text(canonical_json(payload))


def expand_contract() -> dict[str, Any]:
    return {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "parent_review_receipt_sha256": REVIEW_RECEIPT_SHA256,
        "parent_diagnosis": "MIXED_POSITIVE_SEMANTIC_GENERALIZATION_FAILURE",
        "surface_ids": {
            "TRAIN": TRAIN_V3_ID,
            "DEV_SELECTION": DEV_V3_ID,
            "REPRESENTATIVE_VALIDATION": REP_V3_ID,
            "parent_TRAIN": TRAIN_V2_ID,
            "parent_DEV": DEV_V2_ID,
            "parent_REP": REP_V2_ID,
        },
        "frozen": {
            "encoder_model_id": SELECTED_ENCODER_MODEL_ID,
            "encoder_revision": SELECTED_ENCODER_REVISION,
            "ANY_LABEL_threshold": WITNESS_GATE_THRESHOLD,
            "axis_head_architecture": "768→128→ReLU→n_labels",
            "thresholds": dict(BAKEOFF_THRESHOLDS),
            "ontology_changed": False,
            "QUALIFICATION_ID": QUALIFICATION_ID,
            "operating_package_sha256": EXPECTED_PACKAGE_SHA256,
            "operating_package_id": OPERATING_PACKAGE_ID,
        },
        "forbidden": [
            "retune_ANY_LABEL_threshold",
            "modify_NONE_rejection",
            "retrain_encoder",
            "change_ontology",
            "use_QUAL_003_rows_for_training",
            "use_QUAL_003_for_row_level_acquisition_targeting",
            "select_by_model_misclassification",
            "architecture_bakeoff",
            "another_QUAL_surface",
        ],
        "QUALIFICATION_USED_FOR_OPTIMIZATION": False,
        "historical_qual": {
            "QUALIFICATION_ID": QUALIFICATION_ID,
            "seal_sha256": EXPECTED_SEAL_SHA256,
            "result_sha256": EXPECTED_QUAL_RESULT_SHA256,
            "role": "BLOCKED_SPENT_SURFACE",
            "row_reuse_forbidden": True,
        },
        "diversity_targets": {
            "rep_zero_label_share": list(REP_V3_ZERO_LABEL_SHARE_RANGE),
            "rep_min_function_n": REP_V3_MIN_FUNCTION_N,
            "rep_min_function_non_wikt_share": REP_V3_MIN_FUNCTION_NON_WIKT_SHARE,
            "rep_min_function_medium_long_share": REP_V3_MIN_FUNCTION_MEDIUM_LONG_SHARE,
            "rep_min_domain_function_pairs": REP_V3_MIN_DOMAIN_FUNCTION_PAIRS,
            "per_function_min_rep": PER_FUNCTION_MIN_REP,
            "per_function_min_train": PER_FUNCTION_MIN_TRAIN,
            "function_vocab": list(FUNCTION_VOCAB),
        },
        "encoder_use_allowed": [
            "deduplication",
            "coverage_analysis",
            "semantic_diversity_measurement",
        ],
        "train_policy": {
            "train_axis_heads_only": True,
            "keep_NONE_gate_frozen": True,
            "select_on": "DEV_V3",
            "evaluate_on": "REP_V3",
        },
        "parent_rep_v2_witness": {
            "system": WITNESS_REP_SYSTEM_MACRO_F1,
            "positive_only": WITNESS_REP_POSITIVE_ONLY,
            "zero_fp": WITNESS_REP_ZERO_FP,
            "zero_exact": WITNESS_REP_ZERO_EXACT,
            "FUNCTION": 0.22272324177813058,
        },
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "RELEASE_ELIGIBLE": False,
        "outcomes": list(OUTCOMES),
        "next_actions": list(NEXT_ACTIONS),
    }


def source_style(source_family: str) -> str:
    s = (source_family or "").lower()
    if "wiki_none" in s or "wiki_html_none" in s:
        return "encyclopedic_none_cue"
    if "wiki_culture" in s or "wiki_html_pos" in s or "wp_culture" in s:
        return "encyclopedic_positive"
    if "firecrawl" in s:
        return "firecrawl_observed"
    if "wikt" in s:
        return "wiktionary_sense"
    return "other"


def length_bucket(n: int) -> str:
    if n < 60:
        return "short"
    if n < 200:
        return "medium"
    return "long"


def diversity_audit_pass(audit: Mapping[str, Any]) -> dict[str, Any]:
    """Pass/fail diversity gates for V3 surfaces (no QUAL targeting)."""
    rep = dict(audit.get("rep") or {})
    train = dict(audit.get("train") or {})
    zero = float(rep.get("zero_label_share") or 0.0)
    fun_n = int(rep.get("function_n") or 0)
    non_wikt = float(rep.get("function_non_wikt_share") or 0.0)
    med_long = float(rep.get("function_medium_long_share") or 0.0)
    df_pairs = int(rep.get("domain_function_pairs_n") or 0)
    per_rep = dict(rep.get("per_function_support") or {})
    per_train = dict(train.get("per_function_support") or {})
    lo, hi = REP_V3_ZERO_LABEL_SHARE_RANGE

    checks = {
        "rep_zero_label_in_range": lo <= zero <= hi,
        "rep_function_n": fun_n >= REP_V3_MIN_FUNCTION_N,
        "rep_function_non_wikt": non_wikt >= REP_V3_MIN_FUNCTION_NON_WIKT_SHARE,
        "rep_function_medium_long": med_long >= REP_V3_MIN_FUNCTION_MEDIUM_LONG_SHARE,
        "rep_domain_function_pairs": df_pairs >= REP_V3_MIN_DOMAIN_FUNCTION_PAIRS,
        "per_function_rep": all(
            int(per_rep.get(lab) or 0) >= PER_FUNCTION_MIN_REP for lab in FUNCTION_VOCAB
        ),
        "per_function_train": all(
            int(per_train.get(lab) or 0) >= PER_FUNCTION_MIN_TRAIN
            for lab in FUNCTION_VOCAB
        ),
        "disjointness": bool(audit.get("disjointness_pass")),
        "qual003_blocked": bool(audit.get("qual003_blocked")),
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "values": {
            "rep_zero_label_share": zero,
            "rep_function_n": fun_n,
            "rep_function_non_wikt_share": non_wikt,
            "rep_function_medium_long_share": med_long,
            "rep_domain_function_pairs_n": df_pairs,
        },
    }


def none_preserved(metrics: Mapping[str, Any]) -> dict[str, Any]:
    zero_fp = float(metrics.get("zero_label_false_positive_rate") or 1.0)
    zero_ex = float(metrics.get("zero_label_exact_rejection") or 0.0)
    operating_pass = zero_fp <= NONE_ZERO_FP_MAX and zero_ex >= NONE_ZERO_EXACT_MIN
    vs_witness_ok = zero_fp <= (WITNESS_REP_ZERO_FP + NONE_REGRESSION_FP_DELTA_MAX)
    return {
        "pass": operating_pass,
        "operating_gates_pass": operating_pass,
        "vs_witness_fp_ok": vs_witness_ok,
        "zero_label_false_positive_rate": zero_fp,
        "zero_label_exact_rejection": zero_ex,
        "witness_zero_fp": WITNESS_REP_ZERO_FP,
        "witness_zero_exact": WITNESS_REP_ZERO_EXACT,
    }


def classify_outcome(
    *,
    diversity_pass: bool,
    none: Mapping[str, Any],
    candidate: Mapping[str, Any],
    baseline: Mapping[str, Any],
) -> dict[str, Any]:
    """Advance iff FUNCTION + positive-only improve and NONE is preserved."""
    fun_c = float(candidate.get("FUNCTION_macro_f1") or 0.0)
    fun_b = float(baseline.get("FUNCTION_macro_f1") or 0.0)
    pos_c = float(candidate.get("positive_only_system_macro_f1") or 0.0)
    pos_b = float(baseline.get("positive_only_system_macro_f1") or 0.0)
    sys_c = float(candidate.get("system_macro_f1") or 0.0)
    sys_b = float(baseline.get("system_macro_f1") or 0.0)

    fun_up = fun_c >= fun_b + 0.03
    pos_up = pos_c >= pos_b + 0.02
    none_ok = bool(none.get("pass"))
    adequate_support = diversity_pass

    if not adequate_support:
        outcome = "V6_FUNCTION_DIVERSITY_NO_ADVANCE"
        next_action = "CONTINUE_V6_FUNCTION_DATA_ACQUISITION"
    elif none_ok and fun_up and pos_up:
        outcome = "V6_FUNCTION_DIVERSITY_ADVANCE"
        next_action = "HARDEN_V6_POSITIVE_SEMANTIC_GENERALIZATION"
    elif none_ok and (fun_up or pos_up or sys_c >= sys_b + 0.02):
        outcome = "V6_FUNCTION_DIVERSITY_PARTIAL"
        # Diverse support present but function still weak → redesign prediction
        if fun_c < 0.18 and adequate_support:
            next_action = "REDESIGN_V6_FUNCTION_PREDICTION"
        else:
            next_action = "CONTINUE_V6_FUNCTION_DATA_ACQUISITION"
    elif adequate_support and none_ok and fun_c < fun_b + 0.03:
        outcome = "V6_FUNCTION_DIVERSITY_NO_ADVANCE"
        next_action = "REDESIGN_V6_FUNCTION_PREDICTION"
    else:
        outcome = "V6_FUNCTION_DIVERSITY_NO_ADVANCE"
        next_action = "CONTINUE_V6_FUNCTION_DATA_ACQUISITION"

    return {
        "OUTCOME": outcome,
        "NEXT_ACTION": next_action,
        "function_delta": fun_c - fun_b,
        "positive_only_delta": pos_c - pos_b,
        "system_delta": sys_c - sys_b,
        "none_preserved": none_ok,
        "diversity_pass": adequate_support,
    }


def build_expand_receipt(body: Mapping[str, Any], *, sealed_at: str) -> dict[str, Any]:
    out = dict(body)
    out.update(
        {
            "PHASE_RULE": PHASE_RULE,
            "EXPERIMENT_ID": EXPERIMENT_ID,
            "schema": SCHEMA,
            "QUALIFICATION_USED_FOR_OPTIMIZATION": False,
            "HUB_PUBLISH_AUTHORIZED": False,
            "RELEASE_ELIGIBLE": False,
            "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
            "MODEL_WIDE_BEST_MUTATED": False,
            "V6_OPERATING_PIPELINE_CANDIDATE_MUTATED": False,
            "NONE_GATE_MUTATED": False,
            "ANY_LABEL_THRESHOLD_MUTATED": False,
            "ENCODER_MUTATED": False,
            "ONTOLOGY_MUTATED": False,
            "sealed_at": sealed_at,
        }
    )
    out["SYSTEM_EXPAND_RECEIPT_SHA256"] = _hash(
        {k: v for k, v in out.items() if k != "SYSTEM_EXPAND_RECEIPT_SHA256"}
    )
    return out


__all__ = [
    "BAKEOFF_THRESHOLDS",
    "DEV_V3_ID",
    "EXPERIMENT_ID",
    "FUNCTION_VOCAB",
    "NEXT_ACTIONS",
    "OUTCOMES",
    "PHASE_RULE",
    "REP_V3_ID",
    "REVIEW_RECEIPT_SHA256",
    "TRAIN_V3_ID",
    "build_expand_receipt",
    "classify_outcome",
    "diversity_audit_pass",
    "expand_contract",
    "length_bucket",
    "none_preserved",
    "source_style",
]
