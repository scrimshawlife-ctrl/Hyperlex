"""BUILD_AND_SEAL_FRESH_V6_QUALIFICATION_SURFACE_003 — contracts.

Model-blind construction of HYPERLEX_V6_QUALIFICATION_003 under the final
ontology and operating-distribution gates. QUAL-002 remains EVALUATION_SPENT.
No scoring of the operating pipeline package.
"""

from __future__ import annotations

from typing import Any, Mapping

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
from .classification_v6_operating_pipeline_harden import (
    OPERATING_QUALIFICATION_GATES,
    PACKAGE_ID as OPERATING_PACKAGE_ID,
    operating_error_taxonomy,
    operating_qualification_metrics,
)
from .classification_v6_qualification_execute_002 import (
    EXPECTED_PACKAGE_SHA256 as PARENT_HARDENED_PACKAGE_SHA,
)
from .classification_v6_qualification_surface_002 import (
    QUALIFICATION_ID as QUAL_002_ID,
)
from .classification_v6_semantic_pipeline_harden import pipeline_candidate_contract

PHASE_RULE = "BUILD_AND_SEAL_FRESH_V6_QUALIFICATION_SURFACE_003"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-QUALIFICATION-SURFACE-003"
QUALIFICATION_ID = "HYPERLEX_V6_QUALIFICATION_003"
HISTORICAL_QUAL_002_ID = QUAL_002_ID
HISTORICAL_QUAL_001_ID = "HYPERLEX_V6_QUALIFICATION_001"
SCHEMA = "hyperlex.classification.v6.qualification_surface_003.v1"

# Operating package bound for later scoring — not loaded against QUAL rows here.
OPERATING_PACKAGE_SHA256 = (
    "8ed1a4d45d37a4cfb1ad12c0c50fd37007daa772f3cdfee35cdc454055c3699a"
)

PRIOR_MEAN_SET_JACCARD = 0.969
AGREEMENT_COLLAPSE_FLOOR = 0.80

TARGET_N_MIN = 750
TARGET_N_PREFERRED = 1000
PREFERRED_POSITIVES_PER_LABEL = 25
MAX_SOURCE_FAMILY_SHARE = 0.25

# Operating-distribution guidance (not exact QUAL-002 copy).
ZERO_LABEL_SHARE_RANGE = (0.40, 0.80)
NO_EVIDENCE_SHARE_RANGE = (0.35, 0.75)

SURFACE_STATES = (
    "V6_QUALIFICATION_003_SURFACE_SEALED",
    "V6_QUALIFICATION_003_SURFACE_PARTIAL",
    "V6_QUALIFICATION_003_SURFACE_INVALID",
)


def _hash(payload: Any) -> str:
    return sha256_text(canonical_json(payload))


def ontology_binding() -> dict[str, Any]:
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
        "runtime_schema": (
            "hyperlex.classification.v6.operating_gated_hierarchical_forward.v1"
        ),
        "operating_package_sha": OPERATING_PACKAGE_SHA256,
        "parent_hardened_package_sha": PARENT_HARDENED_PACKAGE_SHA,
    }
    binding = {
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "ontology_version": FINAL_ONTOLOGY_ID,
        "structure": "HIERARCHICAL_MULTI_LABEL",
        "label_schema": label_schema,
        "hierarchy": hierarchy,
        "input_contract": input_contract,
        "pipeline_candidate_ref": OPERATING_PACKAGE_ID,
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
            "QUAL_002_rows",
            "operating_package_scores",
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
    """Bind operating QUAL gates — frozen before QUAL-003 open."""
    return {
        "source": "HLX-CLASSIFICATION-V6-OPERATING-PIPELINE-HARDEN-001",
        "gates": dict(OPERATING_QUALIFICATION_GATES),
        "metrics": operating_qualification_metrics(),
        "error_taxonomy": operating_error_taxonomy(),
        "modified_in_this_phase": False,
        "operating_package_sha256": OPERATING_PACKAGE_SHA256,
        "QUAL_002_status": "EVALUATION_SPENT",
        "chosen_before_qual_scoring": True,
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
        "zero_label_share_guidance": list(ZERO_LABEL_SHARE_RANGE),
        "no_evidence_share_guidance": list(NO_EVIDENCE_SHARE_RANGE),
        "preserve_natural_prevalence": True,
        "force_equal_balance_forbidden": True,
        "do_not_copy_QUAL_002_prevalence": True,
    }


def qual_003_contract() -> dict[str, Any]:
    binding = ontology_binding()
    return {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "historical": {
            "QUAL_001": {
                "id": HISTORICAL_QUAL_001_ID,
                "status": "HISTORICAL_SEALED_UNINSPECTED",
                "reuse_forbidden": True,
            },
            "QUAL_002": {
                "id": HISTORICAL_QUAL_002_ID,
                "status": "EVALUATION_SPENT",
                "reuse_forbidden": True,
                "row_access": False,
            },
        },
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
            "score_QUAL_003",
            "load_operating_package_against_QUAL_rows",
            "tune_thresholds",
            "modify_heads",
            "modify_gate",
            "change_ontology",
            "reuse_QUAL_002_rows",
            "reuse_TRAIN_DEV_REP_V2",
            "synthetic_padding",
            "model_influenced_inclusion",
        ],
        "pointer_policy": {
            "MODEL_WIDE_BEST": "UNCHANGED",
            "V6_OPERATING_PIPELINE_CANDIDATE": "UNCHANGED",
            "V5_pointers": "UNCHANGED",
        },
        "evaluation_spend": {
            "initial": "UNSPENT",
            "after_first_canonical_score": "EVALUATION_SPENT",
        },
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "HUB_PUBLISH_AUTHORIZED": False,
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
            "SURFACE_STATE": "V6_QUALIFICATION_003_SURFACE_INVALID",
            "NEXT_ACTION": "REVIEW_V6_QUALIFICATION_003_GOLD",
            "reason": "qualification_model_executions_nonzero",
        }
    if not ontology_compatible or not identifiability_pass or not disjointness_pass:
        return {
            "SURFACE_STATE": "V6_QUALIFICATION_003_SURFACE_INVALID",
            "NEXT_ACTION": "CONTINUE_V6_QUALIFICATION_003_ACQUISITION",
            "reason": "ontology_identifiability_or_disjointness_failed",
        }
    if not gold_stable:
        return {
            "SURFACE_STATE": "V6_QUALIFICATION_003_SURFACE_INVALID",
            "NEXT_ACTION": "REVIEW_V6_QUALIFICATION_003_GOLD",
            "reason": "QUALIFICATION_GOLD_UNSTABLE",
        }
    if seal_complete and coverage_sufficient and n_rows >= TARGET_N_MIN:
        return {
            "SURFACE_STATE": "V6_QUALIFICATION_003_SURFACE_SEALED",
            "NEXT_ACTION": "EXECUTE_V6_QUALIFICATION_003_ONCE",
            "reason": "all_seal_gates_passed",
        }
    if n_rows > 0 and (
        not coverage_sufficient or n_rows < TARGET_N_MIN or not seal_complete
    ):
        return {
            "SURFACE_STATE": "V6_QUALIFICATION_003_SURFACE_PARTIAL",
            "NEXT_ACTION": "CONTINUE_V6_QUALIFICATION_003_ACQUISITION",
            "reason": "coverage_or_volume_insufficient",
        }
    return {
        "SURFACE_STATE": "V6_QUALIFICATION_003_SURFACE_INVALID",
        "NEXT_ACTION": "CONTINUE_V6_QUALIFICATION_003_ACQUISITION",
        "reason": "empty_or_unsealed",
    }


def coverage_sufficient_operating(summary: Mapping[str, Any]) -> bool:
    """Volume + axis support + operating-aware zero-label mass."""
    n = int(summary.get("n") or 0)
    stage = summary.get("stage_a") or {}
    card = summary.get("cardinality") or {}
    zero_share = float(summary.get("zero_label_share") or 0.0)
    no_ev = int(stage.get("NO_EVIDENCE") or 0)
    active_dom = int(summary.get("active_domain_labels") or 0)
    active_fun = int(summary.get("active_function_labels") or 0)
    med = int((summary.get("mediation_supports") or {}).get("mediation.internet_register") or 0)
    multi = int(card.get("2") or 0) + int(card.get("3+") or 0)
    return (
        n >= TARGET_N_MIN
        and active_dom >= 6
        and active_fun >= 2
        and med >= 10
        and multi >= 30
        and int(stage.get("EVIDENCE_PRESENT") or 0) >= 100
        and no_ev >= 200
        and zero_share >= ZERO_LABEL_SHARE_RANGE[0]
    )


__all__ = [
    "AGREEMENT_COLLAPSE_FLOOR",
    "EXPERIMENT_ID",
    "MAX_SOURCE_FAMILY_SHARE",
    "OPERATING_PACKAGE_SHA256",
    "PHASE_RULE",
    "PREFERRED_POSITIVES_PER_LABEL",
    "PRIOR_MEAN_SET_JACCARD",
    "QUALIFICATION_ID",
    "TARGET_N_MIN",
    "TARGET_N_PREFERRED",
    "ZERO_LABEL_SHARE_RANGE",
    "classify_agreement_stability",
    "coverage_sufficient_operating",
    "coverage_targets",
    "decide_surface_state",
    "gate_binding",
    "ontology_binding",
    "qual_003_contract",
]
