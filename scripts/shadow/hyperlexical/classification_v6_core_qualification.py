"""HYPERLEX_V6_CORE_QUALIFICATION_001 — surface, execute, release contracts.

Fresh core qualification under evidence_gate + DOMAIN + MEDIATION.
FUNCTION is advisory/non-blocking and must not influence surface inclusion,
balancing, gates, or release disposition.
"""

from __future__ import annotations

from typing import Any, Mapping

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
from .classification_v5_stage_a_gold_identifiability_contract import (
    CONTRACT_ID as GOLD_CONTRACT_ID,
    MODEL_INPUT,
)
from .classification_v6_core_product_harden import (
    CORE_QUALIFICATION_GATES,
    CORE_WITNESS_REP_V3,
    EXPERIMENT_ID as PARENT_HARDEN_EXPERIMENT,
    PACKAGE_ID as CORE_PACKAGE_ID,
    POINTER_ID as CORE_POINTER_ID,
    QUAL_CORE_ID,
    RUNTIME_SCHEMA,
    core_output_contract,
)
from .classification_v6_human_ontology_settlement import FINAL_ONTOLOGY_ID
from .classification_v6_label_migration import (
    DOMAIN_VOCAB,
    FUNCTION_VOCAB,
    MEDIATION_VOCAB,
)
from .classification_v6_operating_pipeline_harden import (
    WITNESS_GATE_BUNDLE_SHA256,
    WITNESS_GATE_THRESHOLD,
)
from .classification_v6_qualification_execute_002 import (
    EXPECTED_ENCODER_STATE_HASH,
    EXPECTED_HEAD_BUNDLE_SHA256 as _EXPECTED_HEAD_BUNDLE_SHA256,
)
from .classification_v6_qualification_execute_003 import (
    EXPECTED_SEAL_SHA256 as QUAL_003_SEAL_SHA256,
    QUALIFICATION_ID as QUAL_003_ID,
)
from .classification_v6_qualification_surface_002 import (
    QUALIFICATION_ID as QUAL_002_ID,
)
from .classification_v6_semantic_pipeline_harden import (
    BAKEOFF_THRESHOLDS,
    SELECTED_ENCODER_MODEL_ID,
    SELECTED_ENCODER_REVISION,
    hierarchy_constraints_payload,
    label_schema_payload,
    pipeline_candidate_contract,
    threshold_manifest_payload,
)

PHASE_RULE = "BUILD_SEAL_EXECUTE_V6_CORE_QUALIFICATION_AND_RELEASE_DECISION"
SURFACE_PHASE = "BUILD_AND_SEAL_FRESH_V6_CORE_QUALIFICATION_SURFACE"
EXECUTE_PHASE = "EXECUTE_V6_CORE_QUALIFICATION_ONCE"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-CORE-QUALIFICATION-001"
SURFACE_EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-CORE-QUALIFICATION-SURFACE-001"
EXECUTE_EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-CORE-QUALIFICATION-EXECUTE-001"
QUALIFICATION_ID = QUAL_CORE_ID  # HYPERLEX_V6_CORE_QUALIFICATION_001
RESULT_ID = "HYPERLEX_V6_CORE_QUALIFICATION_001_RESULT"
SCHEMA = "hyperlex.classification.v6.core_qualification.v1"
SURFACE_SCHEMA = "hyperlex.classification.v6.core_qualification_surface.v1"
EXECUTE_SCHEMA = "hyperlex.classification.v6.core_qualification_execute.v1"

# Hardened core package — must match cold-load identity exactly.
EXPECTED_PACKAGE_SHA256 = (
    "035e1b7e21e97ed36f79750f1f643262540fba1546f488af2a0af04e8a7c1605"
)
EXPECTED_GATE_BUNDLE_SHA256 = WITNESS_GATE_BUNDLE_SHA256
EXPECTED_GATE_THRESHOLD = WITNESS_GATE_THRESHOLD
EXPECTED_HEAD_BUNDLE_SHA256 = _EXPECTED_HEAD_BUNDLE_SHA256
HISTORICAL_QUAL_001_ID = "HYPERLEX_V6_QUALIFICATION_001"

# REP_V3 core witness (diagnostic retention only; not a hard gate).
REP_CORE_SYSTEM = float(CORE_WITNESS_REP_V3["core_system_macro_f1"])
REP_DOMAIN = float(CORE_WITNESS_REP_V3["DOMAIN_macro_f1"])
REP_MEDIATION = float(CORE_WITNESS_REP_V3["MEDIATION_macro_f1"])
REP_ZERO_FP = float(CORE_WITNESS_REP_V3["zero_label_false_positive_rate"])
REP_ZERO_EXACT = float(CORE_WITNESS_REP_V3["zero_label_exact_rejection"])

TARGET_N_MIN = 750
TARGET_N_PREFERRED = 1000
PREFERRED_POSITIVES_PER_LABEL = 20
MAX_SOURCE_FAMILY_SHARE = 0.30
ZERO_LABEL_SHARE_RANGE = (0.55, 0.75)
AGREEMENT_COLLAPSE_FLOOR = 0.80
PRIOR_MEAN_CORE_JACCARD = 0.90

RETENTION_BANDS = {
    "STRONG_RETENTION": 0.85,
    "MODERATE_RETENTION": 0.70,
    "SEVERE_GENERALIZATION_DROP": 0.0,
}

SURFACE_STATES = (
    "V6_CORE_QUALIFICATION_SURFACE_SEALED",
    "V6_CORE_QUALIFICATION_SURFACE_PARTIAL",
    "V6_CORE_QUALIFICATION_SURFACE_INVALID",
)

QUAL_DISPOSITIONS = (
    "V6_CORE_QUALIFICATION_PASS",
    "V6_CORE_QUALIFICATION_FAIL",
    "V6_CORE_QUALIFICATION_INVALID",
)

RELEASE_OUTCOMES = (
    "V6_CORE_RELEASE_CANDIDATE_APPROVED",
    "V6_CORE_RELEASE_CANDIDATE_REJECTED",
)

FAILURE_CLASSES = (
    "EVIDENCE_GATE_FAILURE",
    "DOMAIN_GENERALIZATION_FAILURE",
    "MEDIATION_GENERALIZATION_FAILURE",
    "MIXED_CORE_GENERALIZATION_FAILURE",
)

RELEASE_CANDIDATE_POINTER = "V6_CORE_RELEASE_CANDIDATE"


def _hash(payload: Any) -> str:
    return sha256_text(canonical_json(payload))


def _metric_float(metrics: Mapping[str, Any], key: str, default: float) -> float:
    if key not in metrics or metrics[key] is None:
        return float(default)
    return float(metrics[key])


def ontology_binding() -> dict[str, Any]:
    cand = pipeline_candidate_contract()
    label_schema = label_schema_payload()
    constraints = hierarchy_constraints_payload()
    input_contract = {
        "model_input": list(MODEL_INPUT),
        "gold_identifiability_contract": GOLD_CONTRACT_ID,
        "stage_a_text_only": True,
        "runtime_schema": RUNTIME_SCHEMA,
        "core_package_sha": EXPECTED_PACKAGE_SHA256,
        "required_outputs": ["evidence_gate", "domain", "mediation"],
        "optional_outputs": ["function_best_effort"],
    }
    binding = {
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "ontology_version": FINAL_ONTOLOGY_ID,
        "structure": "HIERARCHICAL_MULTI_LABEL",
        "label_schema": {
            "structure": "HIERARCHICAL_MULTI_LABEL",
            "ontology_version": FINAL_ONTOLOGY_ID,
            "domain_labels": list(DOMAIN_VOCAB),
            "function_labels": list(FUNCTION_VOCAB),
            "mediation_labels": list(MEDIATION_VOCAB),
            "semantics": "label_id_stable_no_display_string_lookup",
            "function_role": "OPTIONAL_ANNOTATION_ONLY_NOT_SCORED",
        },
        "hierarchy": {
            "rules": [
                {
                    "child": "domain.technology.ai_discourse",
                    "parent": "domain.technology",
                    "constraint": "required_parent",
                }
            ]
        },
        "input_contract": input_contract,
        "pipeline_candidate_ref": CORE_PACKAGE_ID,
        "label_schema_hash": cand["ontology"]["label_schema_hash"],
        "hierarchy_hash": cand["ontology"]["hierarchy_hash"],
        "compatibility_rule_hash": cand["ontology"]["compatibility_rule_hash"],
        "constraint_manifest_hash": _hash(constraints),
        "ontology_hash": _hash(
            {
                "ontology_version": FINAL_ONTOLOGY_ID,
                "label_schema_hash": cand["ontology"]["label_schema_hash"],
                "hierarchy_hash": cand["ontology"]["hierarchy_hash"],
                "compatibility_rule_hash": cand["ontology"]["compatibility_rule_hash"],
            }
        ),
        "input_contract_hash": _hash(input_contract),
        "pinned_before_acquisition": True,
    }
    binding["ontology_binding_sha256"] = _hash(
        {k: v for k, v in binding.items() if k != "ontology_binding_sha256"}
    )
    return binding


def annotation_protocol() -> dict[str, Any]:
    return {
        "n_annotators_min": 2,
        "protocols": [
            "A_DOMAIN_FIRST_INDEPENDENT_TEXT_ONLY",
            "B_MEDIATION_AWARE_INDEPENDENT_TEXT_ONLY",
        ],
        "disagreement": "third_pass_documented_adjudication_intersection_rules",
        "annotators_must_not_see": [
            "V6_model_predictions",
            "semantic_scores",
            "nearest_neighbors",
            "TRAIN_DEV_REP_labels",
            "QUAL_001_rows",
            "QUAL_002_rows",
            "QUAL_003_rows",
            "core_package_scores",
        ],
        "capture": [
            "evidence_disposition",
            "domain_labels[]",
            "mediation_labels[]",
            "ontology_uncertainty",
            "insufficient_context",
            "annotator_disagreement",
            "function_labels[]_optional_research_only",
        ],
        "function_influences_inclusion": False,
        "function_influences_balancing": False,
        "function_influences_gates": False,
        "force_definitive_when_unsupported": False,
        "model_blind": True,
    }


def coverage_targets() -> dict[str, Any]:
    return {
        "n_min": TARGET_N_MIN,
        "n_preferred": TARGET_N_PREFERRED,
        "synthetic_padding_forbidden": True,
        "preferred_positives_per_active_domain": PREFERRED_POSITIVES_PER_LABEL,
        "mediation_positive_and_negative_required": True,
        "max_source_family_share_target": MAX_SOURCE_FAMILY_SHARE,
        "zero_label_share_guidance": list(ZERO_LABEL_SHARE_RANGE),
        "preserve_natural_prevalence": True,
        "force_equal_balance_forbidden": True,
        "do_not_copy_spent_QUAL_prevalence": True,
        "function_labels": "optional_annotation_only_not_used_for_inclusion_or_balance",
        "include": [
            "NO_EVIDENCE_zero_label_traffic",
            "domain_positive_traffic",
            "mediation_traffic",
            "domain_plus_mediation_combinations",
            "source_style_diversity",
            "length_diversity",
        ],
    }


def coverage_sufficient_core(summary: Mapping[str, Any]) -> bool:
    """Volume + DOMAIN/MEDIATION support; FUNCTION not required."""
    n = int(summary.get("n") or 0)
    stage = summary.get("stage_a") or {}
    card = summary.get("cardinality") or {}
    zero_share = float(summary.get("zero_label_share") or 0.0)
    no_ev = int(stage.get("NO_EVIDENCE") or 0)
    active_dom = int(summary.get("active_domain_labels") or 0)
    med = int(
        (summary.get("mediation_supports") or {}).get("mediation.internet_register")
        or 0
    )
    multi = int(card.get("2") or 0) + int(card.get("3+") or 0)
    return (
        n >= TARGET_N_MIN
        and active_dom >= 6
        and med >= 10
        and multi >= 20
        and int(stage.get("EVIDENCE_PRESENT") or 0) >= 100
        and no_ev >= 200
        and zero_share >= ZERO_LABEL_SHARE_RANGE[0]
    )


def classify_agreement_stability(mean_core_jaccard: float) -> str:
    if mean_core_jaccard < AGREEMENT_COLLAPSE_FLOOR:
        return "QUALIFICATION_GOLD_UNSTABLE"
    return "QUALIFICATION_GOLD_STABLE"


def decide_surface_state(
    *,
    ontology_compatible: bool,
    gold_stable: bool,
    identifiability_pass: bool,
    disjointness_pass: bool,
    coverage_sufficient: bool,
    seal_complete: bool,
    model_executions: int,
    n_rows: int,
) -> dict[str, Any]:
    if model_executions != 0:
        return {
            "SURFACE_STATE": "V6_CORE_QUALIFICATION_SURFACE_INVALID",
            "NEXT_ACTION": "REPAIR_V6_CORE_QUALIFICATION_EXECUTION",
            "reason": "qualification_model_executions_nonzero_before_seal",
        }
    if not ontology_compatible or not identifiability_pass or not disjointness_pass:
        return {
            "SURFACE_STATE": "V6_CORE_QUALIFICATION_SURFACE_INVALID",
            "NEXT_ACTION": "CONTINUE_V6_CORE_QUALIFICATION_ACQUISITION",
            "reason": "ontology_identifiability_or_disjointness_failed",
        }
    if not gold_stable:
        return {
            "SURFACE_STATE": "V6_CORE_QUALIFICATION_SURFACE_INVALID",
            "NEXT_ACTION": "REVIEW_V6_CORE_QUALIFICATION_GOLD",
            "reason": "QUALIFICATION_GOLD_UNSTABLE",
        }
    if seal_complete and coverage_sufficient and n_rows >= TARGET_N_MIN:
        return {
            "SURFACE_STATE": "V6_CORE_QUALIFICATION_SURFACE_SEALED",
            "NEXT_ACTION": "EXECUTE_V6_CORE_QUALIFICATION_ONCE",
            "reason": "all_seal_gates_passed",
        }
    if n_rows > 0 and (
        not coverage_sufficient or n_rows < TARGET_N_MIN or not seal_complete
    ):
        return {
            "SURFACE_STATE": "V6_CORE_QUALIFICATION_SURFACE_PARTIAL",
            "NEXT_ACTION": "CONTINUE_V6_CORE_QUALIFICATION_ACQUISITION",
            "reason": "coverage_or_volume_insufficient",
        }
    return {
        "SURFACE_STATE": "V6_CORE_QUALIFICATION_SURFACE_INVALID",
        "NEXT_ACTION": "CONTINUE_V6_CORE_QUALIFICATION_ACQUISITION",
        "reason": "empty_or_unsealed",
    }


def surface_contract() -> dict[str, Any]:
    binding = ontology_binding()
    return {
        "PHASE_RULE": SURFACE_PHASE,
        "EXPERIMENT_ID": SURFACE_EXPERIMENT_ID,
        "schema": SURFACE_SCHEMA,
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "parent_harden": {
            "experiment": PARENT_HARDEN_EXPERIMENT,
            "PACKAGE_ID": CORE_PACKAGE_ID,
            "PACKAGE_SHA256": EXPECTED_PACKAGE_SHA256,
            "POINTER_ID": CORE_POINTER_ID,
        },
        "historical": {
            "QUAL_001": {
                "id": HISTORICAL_QUAL_001_ID,
                "status": "HISTORICAL_SEALED_UNINSPECTED",
                "reuse_forbidden": True,
            },
            "QUAL_002": {
                "id": QUAL_002_ID,
                "status": "EVALUATION_SPENT",
                "reuse_forbidden": True,
                "row_access": False,
            },
            "QUAL_003": {
                "id": QUAL_003_ID,
                "status": "EVALUATION_SPENT",
                "seal_sha256": QUAL_003_SEAL_SHA256,
                "reuse_forbidden": True,
                "row_access": False,
            },
        },
        "ontology_binding": binding,
        "annotation_protocol": annotation_protocol(),
        "coverage_targets": coverage_targets(),
        "CORE_QUALIFICATION_GATES": dict(CORE_QUALIFICATION_GATES),
        "gates_chosen_before_qual_open": True,
        "FUNCTION_role": "ADVISORY_ONLY_NON_BLOCKING",
        "agreement": {
            "axes": ["domain", "mediation"],
            "collapse_floor": AGREEMENT_COLLAPSE_FLOOR,
            "collapse_state": "QUALIFICATION_GOLD_UNSTABLE",
            "function_excluded_from_stability": True,
        },
        "forbidden": [
            "score_before_seal",
            "load_core_package_against_QUAL_rows_before_seal",
            "tune_thresholds",
            "modify_heads",
            "modify_gate",
            "change_ontology",
            "reuse_QUAL_001_002_003_rows",
            "reuse_TRAIN_DEV_REP_V3",
            "synthetic_padding",
            "model_influenced_inclusion",
            "balance_on_FUNCTION",
            "include_FUNCTION_in_pass_fail",
        ],
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "HUB_PUBLISH_AUTHORIZED": False,
    }


def execute_contract(*, expected_seal_sha256: str | None = None, expected_n_rows: int | None = None) -> dict[str, Any]:
    return {
        "PHASE_RULE": EXECUTE_PHASE,
        "EXPERIMENT_ID": EXECUTE_EXPERIMENT_ID,
        "schema": EXECUTE_SCHEMA,
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "RESULT_ID": RESULT_ID,
        "PACKAGE_ID": CORE_PACKAGE_ID,
        "runtime_schema": RUNTIME_SCHEMA,
        "output_contract": core_output_contract(),
        "expected": {
            "seal_sha256": expected_seal_sha256,
            "package_sha256": EXPECTED_PACKAGE_SHA256,
            "n_rows": expected_n_rows,
            "head_bundle_sha256": EXPECTED_HEAD_BUNDLE_SHA256,
            "gate_bundle_sha256": EXPECTED_GATE_BUNDLE_SHA256,
            "gate_threshold": EXPECTED_GATE_THRESHOLD,
            "encoder_state_hash": EXPECTED_ENCODER_STATE_HASH,
            "encoder_model_id": SELECTED_ENCODER_MODEL_ID,
            "encoder_revision": SELECTED_ENCODER_REVISION,
            "encoder_trainable_parameters": 0,
            "qualification_model_executions_before": 0,
            "qualification_state_before": "SEALED_UNSCORED",
            "core_thresholds": {
                "domain": list(BAKEOFF_THRESHOLDS["domain"]),
                "mediation": list(BAKEOFF_THRESHOLDS["mediation"]),
            },
            "advisory_thresholds": {
                "function": list(BAKEOFF_THRESHOLDS["function"]),
            },
            "threshold_manifest_hash": _hash(threshold_manifest_payload()),
            "constraint_manifest_hash": _hash(hierarchy_constraints_payload()),
        },
        "gates": dict(CORE_QUALIFICATION_GATES),
        "retention": {
            "rep_core_system_macro_f1": REP_CORE_SYSTEM,
            "rep_DOMAIN_macro_f1": REP_DOMAIN,
            "rep_MEDIATION_macro_f1": REP_MEDIATION,
            "rep_zero_fp": REP_ZERO_FP,
            "rep_zero_exact": REP_ZERO_EXACT,
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
            "modify_QUAL_rows_or_gold",
            "inspect_or_reuse_spent_QUAL",
            "exploratory_retries",
            "subset_reruns",
            "include_FUNCTION_in_pass_fail",
            "lower_gates_after_results",
            "mutate_MODEL_WIDE_BEST",
            "auto_publish",
        ],
        "HUB_PUBLISH_AUTHORIZED": False,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
    }


def evaluate_core_qual_gates(metrics: Mapping[str, Any]) -> dict[str, Any]:
    g = CORE_QUALIFICATION_GATES
    gates = {
        "core_system_macro_f1": {
            "value": _metric_float(metrics, "core_system_macro_f1", 0.0),
            "threshold": float(g["core_system_macro_f1_min"]),
            "pass": _metric_float(metrics, "core_system_macro_f1", 0.0)
            >= float(g["core_system_macro_f1_min"]),
        },
        "DOMAIN_macro_f1": {
            "value": _metric_float(metrics, "DOMAIN_macro_f1", 0.0),
            "threshold": float(g["DOMAIN_macro_f1_min"]),
            "pass": _metric_float(metrics, "DOMAIN_macro_f1", 0.0)
            >= float(g["DOMAIN_macro_f1_min"]),
        },
        "MEDIATION_macro_f1": {
            "value": _metric_float(metrics, "MEDIATION_macro_f1", 0.0),
            "threshold": float(g["MEDIATION_macro_f1_min"]),
            "pass": _metric_float(metrics, "MEDIATION_macro_f1", 0.0)
            >= float(g["MEDIATION_macro_f1_min"]),
        },
        "zero_label_false_positive_rate": {
            "value": _metric_float(metrics, "zero_label_false_positive_rate", 1.0),
            "threshold": float(g["zero_label_false_positive_rate_max"]),
            "pass": _metric_float(metrics, "zero_label_false_positive_rate", 1.0)
            <= float(g["zero_label_false_positive_rate_max"]),
        },
        "zero_label_exact_rejection": {
            "value": _metric_float(metrics, "zero_label_exact_rejection", 0.0),
            "threshold": float(g["zero_label_exact_rejection_min"]),
            "pass": _metric_float(metrics, "zero_label_exact_rejection", 0.0)
            >= float(g["zero_label_exact_rejection_min"]),
        },
        "hierarchy_violation": {
            "value": _metric_float(metrics, "hierarchy_violation_rate", 1.0),
            "threshold": float(g["hierarchy_violation_max"]),
            "pass": _metric_float(metrics, "hierarchy_violation_rate", 1.0)
            <= float(g["hierarchy_violation_max"]),
        },
        "mean_predicted_labels_on_zero_gold": {
            "value": _metric_float(metrics, "mean_predicted_labels_on_zero_gold", 99.0),
            "threshold": float(g["mean_predicted_labels_on_zero_gold_max"]),
            "pass": _metric_float(metrics, "mean_predicted_labels_on_zero_gold", 99.0)
            <= float(g["mean_predicted_labels_on_zero_gold_max"]),
            "advisory": False,
        },
    }
    hard_keys = [
        "core_system_macro_f1",
        "DOMAIN_macro_f1",
        "MEDIATION_macro_f1",
        "zero_label_false_positive_rate",
        "zero_label_exact_rejection",
        "hierarchy_violation",
        "mean_predicted_labels_on_zero_gold",
    ]
    return {
        "gates": gates,
        "pass": all(gates[k]["pass"] for k in hard_keys),
        "FUNCTION_affects_pass_fail": False,
    }


def classify_retention(qual_core: float, *, rep_core: float = REP_CORE_SYSTEM) -> dict[str, Any]:
    ratio = float(qual_core) / max(1e-12, float(rep_core))
    drop = float(rep_core) - float(qual_core)
    if ratio >= RETENTION_BANDS["STRONG_RETENTION"]:
        band = "STRONG_RETENTION"
    elif ratio >= RETENTION_BANDS["MODERATE_RETENTION"]:
        band = "MODERATE_RETENTION"
    else:
        band = "SEVERE_GENERALIZATION_DROP"
    return {
        "qual_core_system_macro_f1": float(qual_core),
        "rep_core_system_macro_f1": float(rep_core),
        "absolute_degradation": drop,
        "relative_retention": ratio,
        "band": band,
        "hard_gate": False,
    }


def classify_failure(metrics: Mapping[str, Any], gate_eval: Mapping[str, Any]) -> str | None:
    if gate_eval.get("pass"):
        return None
    checks = gate_eval.get("gates") or {}
    none_fail = (not checks.get("zero_label_false_positive_rate", {}).get("pass", True)) or (
        not checks.get("zero_label_exact_rejection", {}).get("pass", True)
    )
    dom_fail = not checks.get("DOMAIN_macro_f1", {}).get("pass", True)
    med_fail = not checks.get("MEDIATION_macro_f1", {}).get("pass", True)
    if none_fail and not dom_fail and not med_fail:
        return "EVIDENCE_GATE_FAILURE"
    if dom_fail and med_fail:
        return "MIXED_CORE_GENERALIZATION_FAILURE"
    if dom_fail:
        return "DOMAIN_GENERALIZATION_FAILURE"
    if med_fail:
        return "MEDIATION_GENERALIZATION_FAILURE"
    return "MIXED_CORE_GENERALIZATION_FAILURE"


def decide_disposition(
    *,
    preflight_ok: bool,
    execution_ok: bool,
    gate_pass: bool,
) -> dict[str, Any]:
    if not preflight_ok or not execution_ok:
        return {
            "QUALIFICATION_DISPOSITION": "V6_CORE_QUALIFICATION_INVALID",
            "RELEASE_OUTCOME": "V6_CORE_RELEASE_CANDIDATE_REJECTED",
            "RELEASE_ELIGIBLE": False,
            "NEXT_ACTION": "REPAIR_V6_CORE_QUALIFICATION_EXECUTION",
            "HUB_PUBLISH_AUTHORIZED": False,
        }
    if gate_pass:
        return {
            "QUALIFICATION_DISPOSITION": "V6_CORE_QUALIFICATION_PASS",
            "RELEASE_OUTCOME": "V6_CORE_RELEASE_CANDIDATE_APPROVED",
            "RELEASE_ELIGIBLE": True,
            "NEXT_ACTION": "FINALIZE_HYPERLEX_V6_RELEASE_CANDIDATE",
            "HUB_PUBLISH_AUTHORIZED": False,
        }
    return {
        "QUALIFICATION_DISPOSITION": "V6_CORE_QUALIFICATION_FAIL",
        "RELEASE_OUTCOME": "V6_CORE_RELEASE_CANDIDATE_REJECTED",
        "RELEASE_ELIGIBLE": False,
        "NEXT_ACTION": "REVIEW_V6_CORE_QUALIFICATION_FAILURE",
        "HUB_PUBLISH_AUTHORIZED": False,
    }


def runtime_contract() -> dict[str, Any]:
    return {
        "input": ["text"],
        "required_outputs": [
            "evidence_decision",
            "domain_labels[]",
            "mediation_labels[]",
        ],
        "optional_outputs": ["function_labels[]"],
        "optional_outputs_role": "advisory_only",
        "diagnostics": [
            "raw_scores",
            "constraint_adjustments",
            "artifact_version_identities",
        ],
        "runtime_schema": RUNTIME_SCHEMA,
    }


def limitations() -> list[str]:
    return [
        "FUNCTION is not release-qualified as a required capability",
        "memetic_form is research-only",
        "contextual pragmatic inference is outside core text-only scope",
        "qualification evidence applies to the final core contract only",
        "not validation for prior V5/V6 experimental configurations",
        "HUB_PUBLISH_AUTHORIZED remains false unless separately authorized",
    ]


__all__ = [
    "AGREEMENT_COLLAPSE_FLOOR",
    "CORE_PACKAGE_ID",
    "CORE_QUALIFICATION_GATES",
    "EXECUTE_EXPERIMENT_ID",
    "EXECUTE_PHASE",
    "EXPECTED_ENCODER_STATE_HASH",
    "EXPECTED_GATE_BUNDLE_SHA256",
    "EXPECTED_GATE_THRESHOLD",
    "EXPECTED_HEAD_BUNDLE_SHA256",
    "EXPECTED_PACKAGE_SHA256",
    "EXPERIMENT_ID",
    "FAILURE_CLASSES",
    "MAX_SOURCE_FAMILY_SHARE",
    "PHASE_RULE",
    "PREFERRED_POSITIVES_PER_LABEL",
    "QUALIFICATION_ID",
    "QUAL_DISPOSITIONS",
    "RELEASE_CANDIDATE_POINTER",
    "RELEASE_OUTCOMES",
    "REP_CORE_SYSTEM",
    "REP_DOMAIN",
    "REP_MEDIATION",
    "REP_ZERO_EXACT",
    "REP_ZERO_FP",
    "RESULT_ID",
    "RETENTION_BANDS",
    "RUNTIME_SCHEMA",
    "SURFACE_EXPERIMENT_ID",
    "SURFACE_PHASE",
    "SURFACE_STATES",
    "TARGET_N_MIN",
    "TARGET_N_PREFERRED",
    "ZERO_LABEL_SHARE_RANGE",
    "annotation_protocol",
    "classify_agreement_stability",
    "classify_failure",
    "classify_retention",
    "coverage_sufficient_core",
    "coverage_targets",
    "decide_disposition",
    "decide_surface_state",
    "evaluate_core_qual_gates",
    "execute_contract",
    "limitations",
    "ontology_binding",
    "runtime_contract",
    "surface_contract",
]
