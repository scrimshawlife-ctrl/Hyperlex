"""HARDEN_V6_CORE_PRODUCT_WITHOUT_REQUIRED_FUNCTION — contracts.

Hardened V6 core package: evidence_gate + DOMAIN + MEDIATION.
FUNCTION is advisory/non-blocking. memetic_form remains research-only.
No QUAL-002/003 reuse.
"""

from __future__ import annotations

from typing import Any, Mapping

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
from .classification_v6_function_diversity_expand import (
    DEV_V3_ID,
    REP_V3_ID,
    TRAIN_V3_ID,
)
from .classification_v6_function_prediction_redesign import BASELINE_REP_V3
from .classification_v6_function_product_requirement import (
    EXPERIMENT_ID as PARENT_PRODUCT_EXPERIMENT,
)
from .classification_v6_operating_pipeline_harden import (
    PACKAGE_ID as PARENT_OPERATING_PACKAGE_ID,
    WITNESS_GATE_BUNDLE_SHA256,
    WITNESS_GATE_THRESHOLD,
)
from .classification_v6_qualification_003_failure_review import (
    EXPECTED_QUAL_RESULT_SHA256,
)
from .classification_v6_qualification_execute_003 import (
    EXPECTED_PACKAGE_SHA256 as PARENT_PACKAGE_SHA256,
    EXPECTED_SEAL_SHA256,
    QUALIFICATION_ID as QUAL_003_ID,
)
from .classification_v6_qualification_execute_002 import (
    EXPECTED_ENCODER_STATE_HASH,
    QUALIFICATION_ID as QUAL_002_ID,
)
from .classification_v6_semantic_pipeline_harden import (
    BAKEOFF_THRESHOLDS,
    SELECTED_ENCODER_MODEL_ID,
    SELECTED_ENCODER_REVISION,
    hierarchy_constraints_payload,
    label_schema_payload,
    threshold_manifest_payload,
)

PHASE_RULE = "HARDEN_V6_CORE_PRODUCT_WITHOUT_REQUIRED_FUNCTION"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-CORE-PRODUCT-HARDEN-001"
SCHEMA = "hyperlex.classification.v6.core_product_harden.v1"

PACKAGE_ID = "HYPERLEX_V6_CORE_PRODUCT_PACKAGE_V1"
POINTER_ID = "V6_CORE_PRODUCT_CANDIDATE"
RUNTIME_SCHEMA = "hyperlex.classification.v6.core_gated_domain_mediation.v1"
QUAL_CORE_ID = "HYPERLEX_V6_CORE_QUALIFICATION_001"

OUTCOMES = (
    "V6_CORE_PRODUCT_HARDENED",
    "V6_CORE_PRODUCT_PARTIAL",
    "V6_CORE_PRODUCT_BLOCKED",
)

NEXT_ACTIONS = (
    "BUILD_AND_SEAL_FRESH_V6_CORE_QUALIFICATION_SURFACE",
    "REVIEW_V6_CORE_PRODUCT_FAILURE",
)

CORE_AXES = ("domain", "mediation")
ADVISORY_AXIS = "function"

# REP_V3 core witness from product-requirement settlement (c488a39d…).
CORE_WITNESS_REP_V3 = {
    "DOMAIN_macro_f1": BASELINE_REP_V3["DOMAIN_macro_f1"],
    "MEDIATION_macro_f1": BASELINE_REP_V3["MEDIATION_macro_f1"],
    "core_system_macro_f1": (
        BASELINE_REP_V3["DOMAIN_macro_f1"] + BASELINE_REP_V3["MEDIATION_macro_f1"]
    )
    / 2.0,
    "zero_label_false_positive_rate": BASELINE_REP_V3[
        "zero_label_false_positive_rate"
    ],
    "zero_label_exact_rejection": BASELINE_REP_V3["zero_label_exact_rejection"],
    "hierarchy_violation_rate": 0.001985,
    "parent_product_receipt_prefix": "c488a39d",
}

# Preregistered core QUAL gates (frozen before any fresh QUAL surface opens).
# Floors derived from REP_V3 core witness with conservative margin.
CORE_QUALIFICATION_GATES = {
    "core_system_macro_f1_min": 0.30,
    "DOMAIN_macro_f1_min": 0.28,
    "MEDIATION_macro_f1_min": 0.28,
    "zero_label_false_positive_rate_max": 0.20,
    "zero_label_exact_rejection_min": 0.80,
    "mean_predicted_labels_on_zero_gold_max": 1.0,
    "hierarchy_violation_max": 0.02,
    "FUNCTION_in_pass_fail": False,
    "FUNCTION_role": "ADVISORY_ONLY_NON_BLOCKING",
    "chosen_before_qual_open": True,
    "QUAL_002_status": "EVALUATION_SPENT",
    "QUAL_003_status": "EVALUATION_SPENT",
    "QUAL_CORE_id": QUAL_CORE_ID,
    "retention_rule": (
        "QUAL core_system_macro_f1(DOMAIN,MEDIATION) >= 0.30; "
        "FUNCTION does not affect pass/fail"
    ),
}

REPRODUCTION_TOLERANCE = {
    "core_system_abs": 0.02,
    "domain_abs": 0.02,
    "mediation_abs": 0.02,
    "zero_fp_abs": 0.05,
    "zero_exact_abs": 0.05,
}

REJECTED_MICRO_FIXES = {
    "require_FUNCTION_for_release": False,
    "reuse_QUAL_002": False,
    "reuse_QUAL_003": False,
    "retrain_encoder": False,
    "retrain_DOMAIN": False,
    "retrain_MEDIATION": False,
    "modify_NONE_gate": False,
    "change_ontology": False,
}


def _hash(payload: Any) -> str:
    return sha256_text(canonical_json(payload))


def core_product_flow() -> list[str]:
    return [
        "text",
        "frozen_semantic_encoder",
        "frozen_semantic_vector",
        "ANY_LABEL_ZERO_LABEL_gate",
        "if_ZERO_LABEL_emit_empty",
        "else_DOMAIN_and_MEDIATION_heads",
        "hierarchy_compatibility_constraints",
        "core_multi_label_output",
        "optional_FUNCTION_advisory_non_blocking",
    ]


def core_output_contract() -> dict[str, Any]:
    return {
        "required_outputs": ["evidence_gate", "domain", "mediation"],
        "optional_outputs": ["function_best_effort"],
        "research_only": ["function.memetic_form"],
        "parallel_research_tracks": ["function_contextual_enrichment_track"],
        "system_macro_axes": list(CORE_AXES),
        "FUNCTION_blocks_release": False,
        "FUNCTION_in_qualification_pass_fail": False,
        "FUNCTION_reporting": "ADVISORY_ONLY_NON_BLOCKING",
        "ontology_labels_preserved": True,
    }


def core_qualification_preparation() -> dict[str, Any]:
    return {
        "QUALIFICATION_ID": QUAL_CORE_ID,
        "status": "PREPARED_NOT_SEALED",
        "QUAL_002": {
            "id": QUAL_002_ID,
            "status": "EVALUATION_SPENT",
            "reuse_forbidden": True,
            "row_access_this_phase": False,
        },
        "QUAL_003": {
            "id": QUAL_003_ID,
            "status": "EVALUATION_SPENT",
            "seal_sha256": EXPECTED_SEAL_SHA256,
            "result_sha256": EXPECTED_QUAL_RESULT_SHA256,
            "reuse_forbidden": True,
            "row_access_this_phase": False,
        },
        "must_be": [
            "natural",
            "OBSERVED",
            "disjoint_from_TRAIN_DEV_REP_V3_and_spent_QUAL",
            "core_operating_distribution_aware",
        ],
        "distribution_targets": {
            "zero_label_share": [0.55, 0.75],
            "min_n": 750,
            "preferred_n": 1000,
            "include": [
                "NO_EVIDENCE_zero_label_traffic",
                "domain_positive_traffic",
                "mediation_traffic",
                "source_style_diversity",
                "length_diversity",
            ],
            "function_labels": "optional_annotation_only_not_scored_for_pass_fail",
        },
        "gates": dict(CORE_QUALIFICATION_GATES),
        "metrics": [
            "core_system_macro_f1",
            "DOMAIN_macro_f1",
            "DOMAIN_micro_f1",
            "MEDIATION_macro_f1",
            "MEDIATION_micro_f1",
            "zero_label_false_positive_rate",
            "zero_label_exact_rejection",
            "mean_predicted_labels_on_zero_gold",
            "sample_f1",
            "jaccard",
            "hierarchy_violation_rate",
            "FUNCTION_advisory_macro_f1_non_blocking",
        ],
        "scoring_authorized": False,
        "executions": 0,
    }


def core_product_contract() -> dict[str, Any]:
    label_schema = label_schema_payload()
    constraints = hierarchy_constraints_payload()
    thresholds = threshold_manifest_payload()
    # Core thresholds exclude function from release contract (kept for advisory).
    core_thresholds = {
        "domain": list(BAKEOFF_THRESHOLDS["domain"]),
        "mediation": list(BAKEOFF_THRESHOLDS["mediation"]),
    }
    advisory_thresholds = {"function": list(BAKEOFF_THRESHOLDS["function"])}
    return {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "PACKAGE_ID": PACKAGE_ID,
        "POINTER_ID": POINTER_ID,
        "parent": {
            "product_requirement_experiment": PARENT_PRODUCT_EXPERIMENT,
            "product_disposition": "FUNCTION_RETAIN_OPTIONAL",
            "operating_package_id": PARENT_OPERATING_PACKAGE_ID,
            "operating_package_sha256": PARENT_PACKAGE_SHA256,
            "product_receipt_prefix": CORE_WITNESS_REP_V3[
                "parent_product_receipt_prefix"
            ],
        },
        "surfaces": {
            "TRAIN": TRAIN_V3_ID,
            "DEV_SELECTION": DEV_V3_ID,
            "REPRESENTATIVE_VALIDATION": REP_V3_ID,
        },
        "output_contract": core_output_contract(),
        "architecture": {
            "flow": core_product_flow(),
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
            "required_heads": ["domain", "mediation"],
            "advisory_heads": ["function"],
            "core_thresholds": core_thresholds,
            "advisory_thresholds": advisory_thresholds,
        },
        "ontology": {
            "label_schema": label_schema,
            "constraints": constraints,
            "label_schema_hash": _hash(label_schema),
            "constraint_manifest_hash": _hash(constraints),
            "threshold_manifest_hash": _hash(thresholds),
            "changed": False,
        },
        "runtime_schema": RUNTIME_SCHEMA,
        "core_witness_REP_V3": dict(CORE_WITNESS_REP_V3),
        "reproduction_tolerance": dict(REPRODUCTION_TOLERANCE),
        "qualification_core_preparation": core_qualification_preparation(),
        "outcomes": list(OUTCOMES),
        "next_actions": list(NEXT_ACTIONS),
        "forbidden": [
            "score_QUAL_002",
            "score_QUAL_003",
            "include_FUNCTION_in_core_pass_fail",
            "retrain_encoder",
            "retrain_DOMAIN",
            "retrain_MEDIATION",
            "modify_NONE_gate",
            "change_ontology",
            "lower_gates_after_results",
        ],
        "QUALIFICATION_USED_FOR_OPTIMIZATION": False,
        "QUAL_002_RESCORED": False,
        "QUAL_003_RESCORED": False,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "RELEASE_ELIGIBLE": False,
        "rejected_micro_fixes_default": dict(REJECTED_MICRO_FIXES),
    }


def evaluate_core_gates(metrics: Mapping[str, Any]) -> dict[str, Any]:
    gates = CORE_QUALIFICATION_GATES
    checks = {
        "core_system": float(metrics.get("core_system_macro_f1") or 0.0)
        >= float(gates["core_system_macro_f1_min"]),
        "DOMAIN": float(metrics.get("DOMAIN_macro_f1") or 0.0)
        >= float(gates["DOMAIN_macro_f1_min"]),
        "MEDIATION": float(metrics.get("MEDIATION_macro_f1") or 0.0)
        >= float(gates["MEDIATION_macro_f1_min"]),
        "zero_fp": float(metrics.get("zero_label_false_positive_rate") or 1.0)
        <= float(gates["zero_label_false_positive_rate_max"]),
        "zero_exact": float(metrics.get("zero_label_exact_rejection") or 0.0)
        >= float(gates["zero_label_exact_rejection_min"]),
        "mean_pred_zero": float(
            metrics.get("mean_predicted_labels_on_zero_gold") or 99.0
        )
        <= float(gates["mean_predicted_labels_on_zero_gold_max"]),
        "hierarchy": float(metrics.get("hierarchy_violation_rate") or 1.0)
        <= float(gates["hierarchy_violation_max"]),
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "FUNCTION_affects_pass_fail": False,
    }


def classify_core_harden_outcome(audit: Mapping[str, Any]) -> dict[str, Any]:
    package_ok = bool(audit.get("package_ok"))
    cold_ok = bool(audit.get("cold_load_ok"))
    round_ok = bool(audit.get("round_trip_ok"))
    encoder_ok = bool(audit.get("encoder_immutable"))
    rep_gates = dict(audit.get("rep_gate_eval") or {})
    dev_gates = dict(audit.get("dev_gate_eval") or {})
    rep_pass = bool(rep_gates.get("pass"))
    dev_pass = bool(dev_gates.get("pass"))
    function_non_blocking = bool(audit.get("function_advisory_non_blocking", True))

    if (
        package_ok
        and cold_ok
        and round_ok
        and encoder_ok
        and rep_pass
        and function_non_blocking
    ):
        return {
            "OUTCOME": "V6_CORE_PRODUCT_HARDENED",
            "NEXT_ACTION": "BUILD_AND_SEAL_FRESH_V6_CORE_QUALIFICATION_SURFACE",
            "QUALIFICATION_READINESS": "V6_CORE_QUALIFICATION_PREP_COMPLETE_SURFACE_REQUIRED",
            "reason": "core_package_cold_load_roundtrip_and_REP_gates_pass",
        }
    if package_ok and cold_ok and encoder_ok and (rep_pass or dev_pass):
        return {
            "OUTCOME": "V6_CORE_PRODUCT_PARTIAL",
            "NEXT_ACTION": "REVIEW_V6_CORE_PRODUCT_FAILURE",
            "QUALIFICATION_READINESS": "V6_CORE_QUALIFICATION_BLOCKED_PACKAGE",
            "reason": "partial_harden_or_roundtrip_or_gate_soft_miss",
        }
    return {
        "OUTCOME": "V6_CORE_PRODUCT_BLOCKED",
        "NEXT_ACTION": "REVIEW_V6_CORE_PRODUCT_FAILURE",
        "QUALIFICATION_READINESS": "V6_CORE_QUALIFICATION_BLOCKED_PACKAGE",
        "reason": "core_unstable_or_package_failed",
    }


def build_core_harden_receipt(
    audit: Mapping[str, Any], *, sealed_at: str
) -> dict[str, Any]:
    decision = classify_core_harden_outcome(audit)
    body = {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "PACKAGE_ID": PACKAGE_ID,
        "OUTCOME": decision["OUTCOME"],
        "NEXT_ACTION": decision["NEXT_ACTION"],
        "QUALIFICATION_READINESS": decision["QUALIFICATION_READINESS"],
        "reason": decision["reason"],
        "output_contract": core_output_contract(),
        "CORE_QUALIFICATION_GATES": dict(CORE_QUALIFICATION_GATES),
        "PACKAGE_SHA256": audit.get("PACKAGE_SHA256"),
        "rep_metrics": dict(audit.get("rep_metrics") or {}),
        "dev_metrics": dict(audit.get("dev_metrics") or {}),
        "function_advisory": dict(audit.get("function_advisory") or {}),
        "REJECTED_MICRO_FIXES": dict(REJECTED_MICRO_FIXES),
        "QUALIFICATION_USED_FOR_OPTIMIZATION": False,
        "QUAL_002_RESCORED": False,
        "QUAL_003_RESCORED": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "RELEASE_ELIGIBLE": decision["OUTCOME"] == "V6_CORE_PRODUCT_HARDENED",
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "DOMAIN_HEAD_MUTATED": False,
        "MEDIATION_HEAD_MUTATED": False,
        "NONE_GATE_MUTATED": False,
        "ENCODER_MUTATED": False,
        "ONTOLOGY_MUTATED": False,
        "FUNCTION_REQUIRED": False,
        "sealed_at": sealed_at,
    }
    body["SYSTEM_CORE_PRODUCT_HARDEN_RECEIPT_SHA256"] = _hash(
        {
            k: v
            for k, v in body.items()
            if k != "SYSTEM_CORE_PRODUCT_HARDEN_RECEIPT_SHA256"
        }
    )
    return body


__all__ = [
    "ADVISORY_AXIS",
    "CORE_AXES",
    "CORE_QUALIFICATION_GATES",
    "CORE_WITNESS_REP_V3",
    "EXPERIMENT_ID",
    "NEXT_ACTIONS",
    "OUTCOMES",
    "PACKAGE_ID",
    "PHASE_RULE",
    "POINTER_ID",
    "QUAL_CORE_ID",
    "REJECTED_MICRO_FIXES",
    "RUNTIME_SCHEMA",
    "build_core_harden_receipt",
    "classify_core_harden_outcome",
    "core_output_contract",
    "core_product_contract",
    "core_product_flow",
    "core_qualification_preparation",
    "evaluate_core_gates",
]
