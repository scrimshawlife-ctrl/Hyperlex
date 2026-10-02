"""REDESIGN_V6_FUNCTION_PREDICTION — contracts.

Redesign FUNCTION prediction only under frozen encoder + frozen ANY_LABEL
gate. DOMAIN and MEDIATION heads stay the sealed old heads. Ontology and
QUAL-003 stay frozen.
"""

from __future__ import annotations

from typing import Any, Mapping

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
from .classification_v6_architecture_reset_bakeoff import LABEL_DESCRIPTIONS
from .classification_v6_function_diversity_expand import (
    DEV_V3_ID,
    REP_V3_ID,
    TRAIN_V3_ID,
)
from .classification_v6_label_migration import FUNCTION_VOCAB
from .classification_v6_operating_pipeline_harden import (
    PACKAGE_ID as OPERATING_PACKAGE_ID,
    WITNESS_GATE_THRESHOLD,
)
from .classification_v6_qualification_003_failure_review import (
    EXPECTED_QUAL_RESULT_SHA256,
)
from .classification_v6_qualification_execute_003 import (
    EXPECTED_PACKAGE_SHA256,
    EXPECTED_SEAL_SHA256,
    QUALIFICATION_ID,
)
from .classification_v6_semantic_pipeline_harden import (
    BAKEOFF_THRESHOLDS,
    SELECTED_ENCODER_MODEL_ID,
    SELECTED_ENCODER_REVISION,
)

PHASE_RULE = "REDESIGN_V6_FUNCTION_PREDICTION"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-FUNCTION-PREDICTION-REDESIGN-001"
SCHEMA = "hyperlex.classification.v6.function_prediction_redesign.v1"

# Sealed old-head baseline on REP_V3 (expand-phase control).
BASELINE_REP_V3 = {
    "system_macro_f1": 0.33108561828189526,
    "DOMAIN_macro_f1": 0.3547754432307839,
    "FUNCTION_macro_f1": 0.2963761484570071,
    "MEDIATION_macro_f1": 0.3421052631578948,
    "positive_only_system_macro_f1": 0.3581232215258432,
    "zero_label_false_positive_rate": 0.08769931662870159,
    "zero_label_exact_rejection": 0.9123006833712984,
}

FORMULATIONS = (
    "INDEPENDENT_BINARY_VERIFIERS",
    "FUNCTION_SEMANTIC_MATCHING",
    "HYBRID_VERIFIER",
)

OUTCOMES = (
    "V6_FUNCTION_PREDICTION_ADVANCE",
    "V6_FUNCTION_PREDICTION_PARTIAL",
    "V6_FUNCTION_PREDICTION_NO_ADVANCE",
)

NEXT_ACTIONS = (
    "HARDEN_V6_FULL_OPERATING_PIPELINE_WITH_REDESIGNED_FUNCTION",
    "REASSESS_V6_FUNCTION_TASK_SIGNAL",
)

# Advancement thresholds (do not lower after results).
FUNCTION_ADVANCE_DELTA = 0.03
SYSTEM_PRESERVE_FLOOR = BASELINE_REP_V3["system_macro_f1"] - 0.01
NONE_ZERO_FP_MAX = 0.35
NONE_ZERO_EXACT_MIN = 0.50
PER_FUNCTION_COLLAPSE_MAX = 0.05

FUNCTION_DEFINITIONS = {
    lab: LABEL_DESCRIPTIONS[lab] for lab in FUNCTION_VOCAB if lab in LABEL_DESCRIPTIONS
}


def _hash(payload: Any) -> str:
    return sha256_text(canonical_json(payload))


def redesign_contract() -> dict[str, Any]:
    return {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "surfaces": {
            "TRAIN": TRAIN_V3_ID,
            "DEV_SELECTION": DEV_V3_ID,
            "REPRESENTATIVE_VALIDATION": REP_V3_ID,
        },
        "frozen": {
            "encoder_model_id": SELECTED_ENCODER_MODEL_ID,
            "encoder_revision": SELECTED_ENCODER_REVISION,
            "ANY_LABEL_threshold": WITNESS_GATE_THRESHOLD,
            "domain_head": "old_axis_nonlinear_heads.pt",
            "mediation_head": "old_axis_nonlinear_heads.pt",
            "ontology_changed": False,
            "thresholds_domain_mediation": {
                "domain": list(BAKEOFF_THRESHOLDS["domain"]),
                "mediation": list(BAKEOFF_THRESHOLDS["mediation"]),
            },
            "operating_package_sha256": EXPECTED_PACKAGE_SHA256,
            "operating_package_id": OPERATING_PACKAGE_ID,
        },
        "function_vocab": list(FUNCTION_VOCAB),
        "function_definitions": dict(FUNCTION_DEFINITIONS),
        "formulations": list(FORMULATIONS),
        "NO_FUNCTION_semantics": "absence_of_all_function_labels_not_fifth_class",
        "negative_design": [
            "other_function_positive",
            "domain_positive_no_function",
            "zero_label_NO_EVIDENCE",
            "semantically_adjacent_function",
        ],
        "selection": "DEV_V3",
        "evaluation": "REP_V3_once",
        "baseline_REP_V3": dict(BASELINE_REP_V3),
        "advancement": {
            "function_macro_f1_min": BASELINE_REP_V3["FUNCTION_macro_f1"]
            + FUNCTION_ADVANCE_DELTA,
            "system_macro_f1_floor": SYSTEM_PRESERVE_FLOOR,
            "preserve_domain_mediation_heads": True,
            "none_zero_fp_max": NONE_ZERO_FP_MAX,
            "none_zero_exact_min": NONE_ZERO_EXACT_MIN,
            "per_function_collapse_max": PER_FUNCTION_COLLAPSE_MAX,
        },
        "forbidden": [
            "retrain_encoder",
            "modify_NONE_gate",
            "retrain_DOMAIN",
            "retrain_MEDIATION",
            "change_ontology",
            "tune_on_QUAL",
            "use_QUAL_003_for_optimization",
            "acquire_more_data_unless_support_deficiency_proven",
            "head_width_optimizer_sweep",
        ],
        "historical_qual": {
            "QUALIFICATION_ID": QUALIFICATION_ID,
            "seal_sha256": EXPECTED_SEAL_SHA256,
            "result_sha256": EXPECTED_QUAL_RESULT_SHA256,
            "role": "BLOCKED_SPENT_SURFACE",
            "row_reuse_forbidden": True,
        },
        "QUALIFICATION_USED_FOR_OPTIMIZATION": False,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "RELEASE_ELIGIBLE": False,
        "outcomes": list(OUTCOMES),
        "next_actions": list(NEXT_ACTIONS),
    }


def none_preserved(metrics: Mapping[str, Any]) -> dict[str, Any]:
    zero_fp = float(metrics.get("zero_label_false_positive_rate") or 1.0)
    zero_ex = float(metrics.get("zero_label_exact_rejection") or 0.0)
    ok = zero_fp <= NONE_ZERO_FP_MAX and zero_ex >= NONE_ZERO_EXACT_MIN
    return {
        "pass": ok,
        "zero_label_false_positive_rate": zero_fp,
        "zero_label_exact_rejection": zero_ex,
    }


def any_function_collapsed(per_label: Mapping[str, Any]) -> bool:
    for lab in FUNCTION_VOCAB:
        row = dict(per_label.get(lab) or {})
        support = int(row.get("support") or 0)
        f1 = float(row.get("f1") or 0.0)
        if support >= 10 and f1 < PER_FUNCTION_COLLAPSE_MAX:
            return True
    return False


def classify_outcome(
    *,
    candidate: Mapping[str, Any],
    baseline: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    base = dict(baseline or BASELINE_REP_V3)
    fun_c = float(candidate.get("FUNCTION_macro_f1") or 0.0)
    fun_b = float(base.get("FUNCTION_macro_f1") or 0.0)
    sys_c = float(candidate.get("system_macro_f1") or 0.0)
    sys_b = float(base.get("system_macro_f1") or 0.0)
    pos_c = float(candidate.get("positive_only_system_macro_f1") or 0.0)
    pos_b = float(base.get("positive_only_system_macro_f1") or 0.0)
    none = none_preserved(candidate)
    collapsed = any_function_collapsed(candidate.get("per_label_function") or {})

    fun_up = fun_c >= fun_b + FUNCTION_ADVANCE_DELTA
    sys_ok = sys_c >= SYSTEM_PRESERVE_FLOOR
    none_ok = bool(none["pass"])

    if fun_up and sys_ok and none_ok and not collapsed:
        outcome = "V6_FUNCTION_PREDICTION_ADVANCE"
        next_action = "HARDEN_V6_FULL_OPERATING_PIPELINE_WITH_REDESIGNED_FUNCTION"
    elif none_ok and (fun_c > fun_b or (fun_c >= fun_b - 0.01 and pos_c >= pos_b)):
        outcome = "V6_FUNCTION_PREDICTION_PARTIAL"
        next_action = "REASSESS_V6_FUNCTION_TASK_SIGNAL"
    else:
        outcome = "V6_FUNCTION_PREDICTION_NO_ADVANCE"
        next_action = "REASSESS_V6_FUNCTION_TASK_SIGNAL"

    return {
        "OUTCOME": outcome,
        "NEXT_ACTION": next_action,
        "function_delta": fun_c - fun_b,
        "system_delta": sys_c - sys_b,
        "positive_only_delta": pos_c - pos_b,
        "none_preserved": none_ok,
        "any_function_collapsed": collapsed,
        "function_advance_threshold": fun_b + FUNCTION_ADVANCE_DELTA,
    }


def select_best_on_dev(candidates: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Pick formulation by DEV FUNCTION macro-F1, tie-break system then pos-only."""
    if not candidates:
        return {"selected": None, "reason": "no_candidates"}
    ranked = sorted(
        candidates,
        key=lambda c: (
            float(c.get("FUNCTION_macro_f1") or 0.0),
            float(c.get("system_macro_f1") or 0.0),
            float(c.get("positive_only_system_macro_f1") or 0.0),
        ),
        reverse=True,
    )
    best = ranked[0]
    return {
        "selected": best.get("formulation"),
        "dev_metrics": {
            "FUNCTION_macro_f1": best.get("FUNCTION_macro_f1"),
            "system_macro_f1": best.get("system_macro_f1"),
            "positive_only_system_macro_f1": best.get("positive_only_system_macro_f1"),
        },
        "ranking": [c.get("formulation") for c in ranked],
    }


def build_redesign_receipt(body: Mapping[str, Any], *, sealed_at: str) -> dict[str, Any]:
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
            "DOMAIN_HEAD_MUTATED": False,
            "MEDIATION_HEAD_MUTATED": False,
            "NONE_GATE_MUTATED": False,
            "ENCODER_MUTATED": False,
            "ONTOLOGY_MUTATED": False,
            "sealed_at": sealed_at,
        }
    )
    out["SYSTEM_FUNCTION_REDESIGN_RECEIPT_SHA256"] = _hash(
        {
            k: v
            for k, v in out.items()
            if k != "SYSTEM_FUNCTION_REDESIGN_RECEIPT_SHA256"
        }
    )
    return out


__all__ = [
    "BASELINE_REP_V3",
    "EXPERIMENT_ID",
    "FORMULATIONS",
    "FUNCTION_DEFINITIONS",
    "FUNCTION_VOCAB",
    "NEXT_ACTIONS",
    "OUTCOMES",
    "PHASE_RULE",
    "build_redesign_receipt",
    "classify_outcome",
    "none_preserved",
    "redesign_contract",
    "select_best_on_dev",
]
