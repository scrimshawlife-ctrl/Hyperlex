"""BUILD_AND_SEAL_FRESH_V6_QUALIFICATION_SURFACE — QUAL-002 contracts.

Model-blind construction of HYPERLEX_V6_QUALIFICATION_002 under the final
hierarchical multi-label ontology. Historical QUAL-001 remains sealed /
uninspected. No scoring of V6_REPRESENTATION_CANDIDATE against QUAL rows.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
from .classification_v5_stage_a_gold_identifiability_contract import (
    CONTRACT_ID as GOLD_CONTRACT_ID,
    MODEL_INPUT,
)
from .classification_v6_human_ontology_settlement import FINAL_ONTOLOGY_ID
from .classification_v6_label_migration import (
    DOMAIN_VOCAB,
    FUNCTION_VOCAB,
    MEDIATION_VOCAB,
)
from .classification_v6_semantic_pipeline_harden import (
    QUALIFICATION_GATES,
    QUALIFICATION_METRICS,
    ERROR_TAXONOMY,
    pipeline_candidate_contract,
)

PHASE_RULE = "BUILD_AND_SEAL_FRESH_V6_QUALIFICATION_SURFACE"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-QUALIFICATION-SURFACE-002"
QUALIFICATION_ID = "HYPERLEX_V6_QUALIFICATION_002"
HISTORICAL_QUAL_ID = "HYPERLEX_V6_QUALIFICATION_001"
SCHEMA = "hyperlex.classification.v6.qualification_surface_002.v1"
PACKAGE_SHA_REF = (
    "a88275837b341b4c549a9c973f5c5190a8f3878be57dffd302e72269d2d560c4"
)

# Settlement witness from human ontology dual-annotation (~0.969 mean set-Jaccard).
PRIOR_MEAN_SET_JACCARD = 0.969
AGREEMENT_COLLAPSE_FLOOR = 0.80  # material collapse vs prior witness → UNSTABLE

TARGET_N_MIN = 750
TARGET_N_PREFERRED = 1000
PREFERRED_POSITIVES_PER_LABEL = 25
MAX_SOURCE_FAMILY_SHARE = 0.25

SURFACE_STATES = (
    "V6_FRESH_QUALIFICATION_SURFACE_SEALED",
    "V6_FRESH_QUALIFICATION_SURFACE_PARTIAL",
    "V6_FRESH_QUALIFICATION_SURFACE_INVALID",
)

HISTORICAL_QUAL_STATUS = {
    "id": HISTORICAL_QUAL_ID,
    "status": "HISTORICAL_SEALED_UNINSPECTED",
    "ontology_status": "ONTOLOGY_INCOMPATIBLE_FOR_FINAL_V6",
    "unsealed": False,
    "rows_inspected": False,
    "role": "HISTORICAL_SECONDARY_ONLY",
}


def _hash(payload: Any) -> str:
    return sha256_text(canonical_json(payload))


def ontology_binding() -> dict[str, Any]:
    """Pin ontology / schema / hierarchy / input contract before acquisition."""
    cand = pipeline_candidate_contract()
    label_schema = {
        "structure": "HIERARCHICAL_MULTI_LABEL",
        "ontology_version": FINAL_ONTOLOGY_ID,
        "domain_labels": list(DOMAIN_VOCAB),
        "function_labels": list(FUNCTION_VOCAB),
        "mediation_labels": list(MEDIATION_VOCAB),
        "semantics": "label_id_stable_no_display_string_lookup",
    }
    hierarchy = {
        "rules": [
            {
                "child": "domain.technology.ai_discourse",
                "parent": "domain.technology",
                "constraint": "required_parent",
            }
        ]
    }
    input_contract = {
        "model_input": list(MODEL_INPUT),
        "gold_identifiability_contract": GOLD_CONTRACT_ID,
        "stage_a_text_only": True,
        "runtime_schema": "hyperlex.classification.v6.semantic_hierarchical_forward.v1",
        "hardened_package_sha": PACKAGE_SHA_REF,
    }
    binding = {
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "ontology_version": FINAL_ONTOLOGY_ID,
        "structure": "HIERARCHICAL_MULTI_LABEL",
        "label_schema": label_schema,
        "hierarchy": hierarchy,
        "co_label_rules_note": "final settled co-label / incompatibility rules",
        "input_contract": input_contract,
        "pipeline_candidate_ref": cand["PIPELINE_CANDIDATE_ID"],
        "label_schema_hash": cand["ontology"]["label_schema_hash"],
        "hierarchy_hash": cand["ontology"]["hierarchy_hash"],
        "compatibility_rule_hash": cand["ontology"]["compatibility_rule_hash"],
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
            "B_FUNCTION_FIRST_INDEPENDENT_TEXT_ONLY",
        ],
        "disagreement": "third_pass_documented_adjudication_intersection_rules",
        "annotators_must_not_see": [
            "V6_model_predictions",
            "semantic_scores",
            "nearest_neighbors",
            "DEV_labels",
            "REP_labels",
            "QUAL_001_rows",
        ],
        "capture": [
            "stage_a",
            "domain_labels[]",
            "function_labels[]",
            "mediation_labels[]",
            "ontology_uncertainty",
            "insufficient_context",
            "annotator_disagreement",
        ],
        "force_definitive_when_unsupported": False,
        "model_blind": True,
    }


def gate_binding() -> dict[str, Any]:
    """Bind already-preregistered harden gates — do not modify."""
    return {
        "source": "HLX-CLASSIFICATION-V6-SEMANTIC-PIPELINE-HARDEN-001",
        "gates": dict(QUALIFICATION_GATES),
        "metrics": list(QUALIFICATION_METRICS),
        "error_taxonomy": list(ERROR_TAXONOMY),
        "modified_in_this_phase": False,
        "axis_collapse": {
            "min_axis_macro_f1": float(QUALIFICATION_GATES["min_axis_macro_f1"]),
            "no_complete_axis_collapse": True,
            "source": "hardening_preregistration",
            "derived_after_qual": False,
        },
        "retention_analysis_preregistration": {
            "report": [
                "QUAL_over_REP_retention_ratio",
                "absolute_drop",
                "per_axis_drop",
                "per_label_drop",
            ],
            "hard_gate": False,
            "bands": {
                "release_quality_generalization": "retention_ratio >= 0.85",
                "moderate_distribution_degradation": "0.70 <= retention_ratio < 0.85",
                "severe_qualification_collapse": "retention_ratio < 0.70",
            },
            "rep_reference_system_macro_f1": 0.4322391331580084,
            "chosen_before_qual_scoring": True,
        },
    }


def coverage_targets() -> dict[str, Any]:
    return {
        "n_min": TARGET_N_MIN,
        "n_preferred": TARGET_N_PREFERRED,
        "synthetic_padding_forbidden": True,
        "preferred_positives_per_active_domain": PREFERRED_POSITIVES_PER_LABEL,
        "preferred_positives_per_active_function": PREFERRED_POSITIVES_PER_LABEL,
        "mediation_positive_and_negative_required": True,
        "max_source_family_share_target": MAX_SOURCE_FAMILY_SHARE,
        "preserve_natural_prevalence": True,
        "force_equal_balance_forbidden": True,
    }


def qual_002_contract() -> dict[str, Any]:
    binding = ontology_binding()
    return {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "historical_qual": HISTORICAL_QUAL_STATUS,
        "ontology_binding": binding,
        "annotation_protocol": annotation_protocol(),
        "gate_binding": gate_binding(),
        "coverage_targets": coverage_targets(),
        "agreement": {
            "prior_mean_set_jaccard_witness": PRIOR_MEAN_SET_JACCARD,
            "collapse_floor": AGREEMENT_COLLAPSE_FLOOR,
            "collapse_state": "QUALIFICATION_GOLD_UNSTABLE",
        },
        "forbidden": [
            "score_QUAL_with_V6_candidate",
            "load_hardened_candidate_against_QUAL_rows",
            "tune_thresholds",
            "modify_heads",
            "change_ontology",
            "inspect_historical_QUAL_001_rows",
            "use_DEV_or_REP_as_QUAL",
            "synthetic_padding",
            "model_influenced_inclusion",
            "compute_V6_embeddings_on_QUAL",
        ],
        "pointer_policy": {
            "MODEL_WIDE_BEST": "UNCHANGED",
            "V6_REPRESENTATION_CANDIDATE": "UNCHANGED",
            "V5_pointers": "UNCHANGED",
        },
        "evaluation_spend": {
            "initial": "UNSPENT",
            "after_first_canonical_score": "EVALUATION_SPENT",
            "never_enter": [
                "TRAIN",
                "DEV",
                "REP",
                "calibration",
                "threshold_tuning",
                "representation_learning",
                "index_construction",
            ],
        },
        "access_control": {
            "model_development": "metadata_only",
            "qualification_execution": "authorized_one_shot_scorer_only",
        },
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
    }


def classify_agreement_stability(mean_set_jaccard: float) -> str:
    if mean_set_jaccard < AGREEMENT_COLLAPSE_FLOOR:
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
            "SURFACE_STATE": "V6_FRESH_QUALIFICATION_SURFACE_INVALID",
            "NEXT_ACTION": "REVIEW_V6_QUALIFICATION_GOLD_INSTABILITY",
            "reason": "qualification_model_executions_nonzero",
        }
    if not ontology_compatible or not identifiability_pass or not disjointness_pass:
        return {
            "SURFACE_STATE": "V6_FRESH_QUALIFICATION_SURFACE_INVALID",
            "NEXT_ACTION": "CONTINUE_V6_FRESH_QUALIFICATION_ACQUISITION",
            "reason": "ontology_identifiability_or_disjointness_failed",
        }
    if not gold_stable:
        return {
            "SURFACE_STATE": "V6_FRESH_QUALIFICATION_SURFACE_INVALID",
            "NEXT_ACTION": "REVIEW_V6_QUALIFICATION_GOLD_INSTABILITY",
            "reason": "QUALIFICATION_GOLD_UNSTABLE",
        }
    if seal_complete and coverage_sufficient and n_rows >= TARGET_N_MIN:
        return {
            "SURFACE_STATE": "V6_FRESH_QUALIFICATION_SURFACE_SEALED",
            "NEXT_ACTION": "EXECUTE_V6_FRESH_QUALIFICATION_ONCE",
            "reason": "all_seal_gates_passed",
        }
    if n_rows > 0 and (not coverage_sufficient or n_rows < TARGET_N_MIN or not seal_complete):
        return {
            "SURFACE_STATE": "V6_FRESH_QUALIFICATION_SURFACE_PARTIAL",
            "NEXT_ACTION": "CONTINUE_V6_FRESH_QUALIFICATION_ACQUISITION",
            "reason": "coverage_or_volume_insufficient",
        }
    return {
        "SURFACE_STATE": "V6_FRESH_QUALIFICATION_SURFACE_INVALID",
        "NEXT_ACTION": "CONTINUE_V6_FRESH_QUALIFICATION_ACQUISITION",
        "reason": "empty_or_unsealed",
    }


def low_qual_support_labels(
    supports: Mapping[str, int],
    *,
    floor: int = PREFERRED_POSITIVES_PER_LABEL,
) -> list[str]:
    return sorted(lab for lab, n in supports.items() if int(n) < floor)


__all__ = [
    "AGREEMENT_COLLAPSE_FLOOR",
    "EXPERIMENT_ID",
    "HISTORICAL_QUAL_STATUS",
    "PHASE_RULE",
    "PRIOR_MEAN_SET_JACCARD",
    "QUALIFICATION_ID",
    "TARGET_N_MIN",
    "TARGET_N_PREFERRED",
    "classify_agreement_stability",
    "decide_surface_state",
    "gate_binding",
    "low_qual_support_labels",
    "ontology_binding",
    "qual_002_contract",
]
