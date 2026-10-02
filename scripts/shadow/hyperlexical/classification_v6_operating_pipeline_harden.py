"""HARDEN_V6_FULL_OPERATING_PIPELINE_AND_PREPARE_NEW_QUALIFICATION.

Package the NONE-rejection ADVANCE candidate (frozen encoder + ANY_LABEL
gate + frozen axis heads + hierarchy) as a cold-loadable operating
pipeline. Preregister QUAL-003 gates under the operating distribution.
QUAL-002 remains EVALUATION_SPENT; do not score any QUAL rows.
"""

from __future__ import annotations

from typing import Any, Mapping

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
from .classification_v6_none_rejection_harden import (
    BASELINE_REP_POSITIVE_ONLY_MACRO_F1,
    CANDIDATE_PACKAGE_ID as NONE_CANDIDATE_ID,
    PIPELINE_POINTER_ID as NONE_POINTER_ID,
)
from .classification_v6_qualification_execute_002 import (
    EXPECTED_ENCODER_STATE_HASH,
    EXPECTED_PACKAGE_SHA256 as PARENT_PACKAGE_SHA256,
    QUALIFICATION_ID as QUAL_002_ID,
)
from .classification_v6_representative_validation_redesign import (
    DEV_V2_ID,
    REP_V2_ID,
    TRAIN_V2_ID,
)
from .classification_v6_semantic_pipeline_harden import (
    BAKEOFF_THRESHOLDS,
    ERROR_TAXONOMY,
    PACKAGE_ID as PARENT_PACKAGE_ID,
    QUALIFICATION_METRICS,
    SELECTED_ENCODER_MODEL_ID,
    SELECTED_ENCODER_REVISION,
    hierarchy_constraints_payload,
    label_schema_payload,
    threshold_manifest_payload,
)

PHASE_RULE = "HARDEN_V6_FULL_OPERATING_PIPELINE_AND_PREPARE_NEW_QUALIFICATION"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-OPERATING-PIPELINE-HARDEN-001"
SCHEMA = "hyperlex.classification.v6.operating_pipeline_harden.v1"

PIPELINE_CANDIDATE_ID = "HYPERLEX_V6_OPERATING_PIPELINE_CANDIDATE_V1"
PACKAGE_ID = "HYPERLEX_V6_OPERATING_PIPELINE_PACKAGE_CANDIDATE_V1"
POINTER_ID = "V6_OPERATING_PIPELINE_CANDIDATE"
RUNTIME_SCHEMA = "hyperlex.classification.v6.operating_gated_hierarchical_forward.v1"
QUAL_003_ID = "HYPERLEX_V6_QUALIFICATION_003"

# Sealed NONE-rejection ADVANCE witnesses (LEARNED_ANY_EVIDENCE_GATE on REP_V2).
WITNESS_REP_SYSTEM_MACRO_F1 = 0.36980892482696165
WITNESS_REP_POSITIVE_ONLY = 0.415797546133708
WITNESS_REP_ZERO_FP = 0.08769931662870159
WITNESS_REP_ZERO_EXACT = 0.9123006833712984
WITNESS_REP_MEAN_PRED_ZERO = 0.14464692482915717
WITNESS_GATE_THRESHOLD = 0.22499999999999998
WITNESS_GATE_BUNDLE_SHA256 = (
    "b7d9381613452944082ba011b950cd74de681de3341fc379bc84a4037f9dc86a"
)

# Reproduction tolerance vs NONE-rejection REP witness.
REPRODUCTION_TOLERANCE = {
    "system_abs": 0.015,
    "zero_fp_abs": 0.05,
    "positive_only_abs": 0.02,
    "pred_mismatch_max": 0,
}

HARDENING_STATES = (
    "V6_OPERATING_PIPELINE_HARDENED",
    "V6_OPERATING_PIPELINE_HARDEN_FAILED",
)

QUALIFICATION_READINESS = (
    "V6_QUALIFICATION_PREP_COMPLETE_SURFACE_REQUIRED",
    "V6_QUALIFICATION_BLOCKED_PACKAGE",
)

# Operating-distribution QUAL gates (preregistered before QUAL-003 open).
OPERATING_QUALIFICATION_GATES = {
    "system_macro_f1_min": 0.30,
    "hierarchy_violation_max": 0.05,
    "min_axis_macro_f1": 0.10,
    "no_complete_axis_collapse": True,
    "zero_label_false_positive_rate_max": 0.35,
    "zero_label_exact_rejection_min": 0.50,
    "positive_only_system_macro_f1_min": 0.30,
    "mean_predicted_labels_on_zero_gold_max": 1.0,
    "retention_rule": (
        "QUAL_system_macro_f1 >= 0.30 preregistered from gated REP≈0.370"
    ),
    "chosen_before_qual_open": True,
    "QUAL_002_status": "EVALUATION_SPENT",
    "QUAL_003_id": QUAL_003_ID,
}


def _hash(payload: Any) -> str:
    return sha256_text(canonical_json(payload))


def operating_pipeline_flow() -> list[str]:
    return [
        "text",
        "frozen_semantic_encoder",
        "frozen_semantic_vector",
        "ANY_LABEL_ZERO_LABEL_gate",
        "if_ZERO_LABEL_emit_empty",
        "else_axis_specific_nonlinear_heads",
        "hierarchy_compatibility_constraints",
        "final_hierarchical_multi_label_output",
    ]


def operating_qualification_metrics() -> list[str]:
    return list(QUALIFICATION_METRICS) + [
        "zero_label_false_positive_rate",
        "zero_label_exact_rejection",
        "mean_predicted_labels_on_zero_gold",
        "positive_only_system_macro_f1",
        "false_reject_positive_rate",
    ]


def operating_error_taxonomy() -> list[str]:
    return list(ERROR_TAXONOMY) + [
        "FALSE_ACCEPT_ZERO",
        "FALSE_REJECT_POSITIVE",
        "GATE_OVER_REJECT",
        "GATE_UNDER_REJECT",
    ]


def qualification_003_preparation() -> dict[str, Any]:
    """Construction plan for QUAL-003 — no rows opened or scored."""
    return {
        "QUALIFICATION_ID": QUAL_003_ID,
        "status": "PREPARED_NOT_SEALED",
        "QUAL_002": {
            "id": QUAL_002_ID,
            "status": "EVALUATION_SPENT",
            "reuse_forbidden": True,
            "row_access_this_phase": False,
        },
        "must_be": [
            "natural",
            "OBSERVED",
            "disjoint_from_TRAIN_V2_DEV_V2_REP_V2_QUAL_002",
            "operating_distribution_aware",
        ],
        "distribution_targets": {
            "zero_label_share": [0.55, 0.75],
            "no_evidence_share": [0.45, 0.70],
            "min_n": 750,
            "preferred_n": 1000,
            "include": [
                "NO_EVIDENCE_zero_label_traffic",
                "positive_traffic",
                "function_labels",
                "multi_label_compositions",
                "source_style_diversity",
                "length_diversity",
            ],
        },
        "annotation": {
            "model_blind": True,
            "n_annotators_min": 2,
            "protocols": [
                "A_DOMAIN_FIRST_INDEPENDENT_TEXT_ONLY",
                "B_FUNCTION_FIRST_INDEPENDENT_TEXT_ONLY",
            ],
        },
        "gates": dict(OPERATING_QUALIFICATION_GATES),
        "metrics": operating_qualification_metrics(),
        "error_taxonomy": operating_error_taxonomy(),
        "scoring_authorized": False,
        "executions": 0,
    }


def operating_pipeline_contract() -> dict[str, Any]:
    label_schema = label_schema_payload()
    constraints = hierarchy_constraints_payload()
    thresholds = threshold_manifest_payload()
    return {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "PIPELINE_CANDIDATE_ID": PIPELINE_CANDIDATE_ID,
        "PACKAGE_ID": PACKAGE_ID,
        "POINTER_ID": POINTER_ID,
        "parent": {
            "PACKAGE_ID": PARENT_PACKAGE_ID,
            "PACKAGE_SHA256": PARENT_PACKAGE_SHA256,
            "NONE_REJECTION_CANDIDATE": NONE_CANDIDATE_ID,
            "NONE_POINTER": NONE_POINTER_ID,
            "mechanism": "LEARNED_ANY_EVIDENCE_GATE",
        },
        "surfaces_frozen": {
            "TRAIN": TRAIN_V2_ID,
            "DEV_SELECTION": DEV_V2_ID,
            "REPRESENTATIVE_VALIDATION": REP_V2_ID,
        },
        "architecture": {
            "flow": operating_pipeline_flow(),
            "gate": {
                "kind": "ANY_SEMANTIC_EVIDENCE_GATE",
                "threshold": WITNESS_GATE_THRESHOLD,
                "bundle_sha256": WITNESS_GATE_BUNDLE_SHA256,
            },
            "encoder": {
                "model_id": SELECTED_ENCODER_MODEL_ID,
                "revision": SELECTED_ENCODER_REVISION,
                "state_hash": EXPECTED_ENCODER_STATE_HASH,
                "trainable": 0,
                "mutable": False,
            },
            "heads": "parent_frozen_axis_nonlinear_heads",
            "thresholds": dict(BAKEOFF_THRESHOLDS),
        },
        "ontology": {
            "label_schema": label_schema,
            "constraints": constraints,
            "label_schema_hash": _hash(label_schema),
            "constraint_manifest_hash": _hash(constraints),
            "threshold_manifest_hash": _hash(thresholds),
        },
        "runtime_schema": RUNTIME_SCHEMA,
        "witness": {
            "REP_V2_system_macro_f1": WITNESS_REP_SYSTEM_MACRO_F1,
            "REP_V2_positive_only_system_macro_f1": WITNESS_REP_POSITIVE_ONLY,
            "REP_V2_zero_label_false_positive_rate": WITNESS_REP_ZERO_FP,
            "REP_V2_zero_label_exact_rejection": WITNESS_REP_ZERO_EXACT,
            "REP_V2_mean_predicted_labels_on_zero_gold": WITNESS_REP_MEAN_PRED_ZERO,
            "positive_only_baseline_pre_gate": BASELINE_REP_POSITIVE_ONLY_MACRO_F1,
        },
        "reproduction_tolerance": dict(REPRODUCTION_TOLERANCE),
        "qualification_003_preparation": qualification_003_preparation(),
        "forbidden": [
            "score_QUAL_002",
            "score_QUAL_003",
            "open_QUAL_rows_for_optimization",
            "retrain_encoder",
            "reopen_ontology",
            "mutate_TRAIN_DEV_REP_V2_definitions",
            "mutate_MODEL_WIDE_BEST",
            "global_promotion",
            "lower_gates_after_results",
        ],
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "RELEASE_ELIGIBLE": False,
    }


def classify_operating_reproduction(metrics: Mapping[str, Any]) -> dict[str, Any]:
    sys_m = float(metrics.get("system_macro_f1") or 0.0)
    zero_fp = float(metrics.get("zero_label_false_positive_rate") or 1.0)
    pos = float(metrics.get("positive_only_system_macro_f1") or 0.0)
    sys_ok = abs(sys_m - WITNESS_REP_SYSTEM_MACRO_F1) <= REPRODUCTION_TOLERANCE[
        "system_abs"
    ]
    zero_ok = abs(zero_fp - WITNESS_REP_ZERO_FP) <= REPRODUCTION_TOLERANCE["zero_fp_abs"]
    pos_ok = abs(pos - WITNESS_REP_POSITIVE_ONLY) <= REPRODUCTION_TOLERANCE[
        "positive_only_abs"
    ]
    ok = sys_ok and zero_ok and pos_ok
    return {
        "reproduction_class": (
            "WITNESS_REPRODUCTION" if ok else "REPRODUCTION_DIVERGED"
        ),
        "sys_ok": sys_ok,
        "zero_ok": zero_ok,
        "pos_ok": pos_ok,
        "observed": {
            "system_macro_f1": sys_m,
            "zero_label_false_positive_rate": zero_fp,
            "positive_only_system_macro_f1": pos,
        },
        "witness": {
            "system_macro_f1": WITNESS_REP_SYSTEM_MACRO_F1,
            "zero_label_false_positive_rate": WITNESS_REP_ZERO_FP,
            "positive_only_system_macro_f1": WITNESS_REP_POSITIVE_ONLY,
        },
    }


def decide_operating_readiness(
    *,
    package_ok: bool,
    cold_load_ok: bool,
    round_trip_ok: bool,
    encoder_immutable: bool,
    reproduction_ok: bool,
) -> dict[str, Any]:
    hardened = (
        package_ok
        and cold_load_ok
        and round_trip_ok
        and encoder_immutable
        and reproduction_ok
    )
    if not hardened:
        return {
            "HARDENING_STATE": "V6_OPERATING_PIPELINE_HARDEN_FAILED",
            "QUALIFICATION_READINESS": "V6_QUALIFICATION_BLOCKED_PACKAGE",
            "NEXT_ACTION": "REVIEW_V6_OPERATING_PIPELINE_HARDENING_FAILURE",
        }
    return {
        "HARDENING_STATE": "V6_OPERATING_PIPELINE_HARDENED",
        "QUALIFICATION_READINESS": "V6_QUALIFICATION_PREP_COMPLETE_SURFACE_REQUIRED",
        "NEXT_ACTION": "BUILD_AND_SEAL_FRESH_V6_QUALIFICATION_SURFACE_003",
    }


def build_operating_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    body = dict(payload)
    body["MODEL_WIDE_BEST"] = MODEL_WIDE_BEST_SHA256
    body["MODEL_WIDE_BEST_MUTATED"] = False
    body["HUB_PUBLISH_AUTHORIZED"] = False
    body["RELEASE_ELIGIBLE"] = False
    body["QUAL_002_ROWS_USED_FOR_OPTIMIZATION"] = False
    body["QUAL_003_SCORED"] = False
    body["schema"] = SCHEMA
    body["V6_OPERATING_PIPELINE_HARDEN_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in body.items()
                if k != "V6_OPERATING_PIPELINE_HARDEN_RECEIPT_SHA256"
            }
        )
    )
    return body


__all__ = [
    "EXPERIMENT_ID",
    "HARDENING_STATES",
    "OPERATING_QUALIFICATION_GATES",
    "PACKAGE_ID",
    "PHASE_RULE",
    "PIPELINE_CANDIDATE_ID",
    "POINTER_ID",
    "QUAL_003_ID",
    "QUALIFICATION_READINESS",
    "REPRODUCTION_TOLERANCE",
    "RUNTIME_SCHEMA",
    "SCHEMA",
    "WITNESS_GATE_BUNDLE_SHA256",
    "WITNESS_GATE_THRESHOLD",
    "WITNESS_REP_MEAN_PRED_ZERO",
    "WITNESS_REP_POSITIVE_ONLY",
    "WITNESS_REP_SYSTEM_MACRO_F1",
    "WITNESS_REP_ZERO_EXACT",
    "WITNESS_REP_ZERO_FP",
    "build_operating_receipt",
    "classify_operating_reproduction",
    "decide_operating_readiness",
    "operating_error_taxonomy",
    "operating_pipeline_contract",
    "operating_pipeline_flow",
    "operating_qualification_metrics",
    "qualification_003_preparation",
]
