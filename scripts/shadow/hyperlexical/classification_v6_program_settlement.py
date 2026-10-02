"""HYPERLEX_PROGRAM_SETTLEMENT — end-state product / research disposition.

Consolidates V5/V6 evidence into one authoritative program settlement.
Does not train models, rescore spent QUAL surfaces, or reopen classifier
micro-cycles. Decision authority: evidence → product role → disposition.
"""

from __future__ import annotations

from typing import Any, Mapping

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
from .classification_v6_core_product_harden import (
    CORE_WITNESS_REP_V3,
    PACKAGE_ID as CORE_PACKAGE_ID,
    QUAL_CORE_ID,
)
from .classification_v6_core_qualification import (
    EXPECTED_PACKAGE_SHA256 as CORE_QUAL_PACKAGE_SHA256,
)

# Sealed CORE QUAL surface identity (spent once; never reuse).
CORE_QUAL_SEAL_SHA256 = (
    "1c36342ea3dcc68e6b70befebf678e378dd56655b8129fd7125f9c421f7c8c27"
)
CORE_PACKAGE_SHA256_PIN = CORE_QUAL_PACKAGE_SHA256
from .classification_v6_function_product_requirement import (
    EXPERIMENT_ID as FUNCTION_PRODUCT_EXPERIMENT,
)
from .classification_v6_semantic_pipeline_harden import (
    SELECTED_ENCODER_MODEL_ID,
    SELECTED_ENCODER_REVISION,
)

PHASE_RULE = "SETTLE_HYPERLEX_PROGRAM_END_STATE"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-PROGRAM-SETTLEMENT-001"
SCHEMA = "hyperlex.classification.v6.program_settlement.v1"

# ---------------------------------------------------------------------------
# Capability grades (Workstream A)
# ---------------------------------------------------------------------------

CAPABILITY_GRADES = (
    "PROVEN",
    "SUPPORTED_BUT_LIMITED",
    "UNRESOLVED",
    "DISPROVEN_FOR_CURRENT_FORMULATION",
)

PRIMARY_DISPOSITIONS = (
    "HYPERLEX_PRODUCTION_CLASSIFIER",
    "HYPERLEX_CONTEXTUAL_SEMANTIC_REASONER",
    "HYPERLEX_REPRESENTATION_AND_MEASUREMENT_LAYER",
    "HYPERLEX_HYBRID_SYSTEM",
    "HYPERLEX_RESEARCH_PLATFORM",
    "HYPERLEX_CLASSIFICATION_PROGRAM_ARCHIVED",
)

RELEASE_STATUSES = (
    "RELEASE_AUTHORIZED",
    "SHADOW_INSTRUMENT_ONLY",
    "RESEARCH_ONLY",
    "REJECTED_NOT_RELEASE_ELIGIBLE",
)

TASK_FORMULATIONS = (
    "classification",
    "semantic_matching",
    "retrieval_plus_verification",
    "contextual_reasoning",
    "candidate_generation",
    "abstaining_decision_system",
    "representation_only_output",
)

# Settled CORE QUAL metrics (HYPERLEX_V6_CORE_QUALIFICATION_001, spent).
CORE_QUAL_METRICS = {
    "QUALIFICATION_ID": QUAL_CORE_ID,
    "PACKAGE_ID": CORE_PACKAGE_ID,
    "PACKAGE_SHA256": CORE_QUAL_PACKAGE_SHA256,
    "seal_sha256": CORE_QUAL_SEAL_SHA256,
    "n_rows": 761,
    "core_system_macro_f1": 0.09437008231962928,
    "DOMAIN_macro_f1": 0.1422285367322818,
    "MEDIATION_macro_f1": 0.046511627906976744,
    "zero_label_false_positive_rate": 0.21308016877637131,
    "zero_label_exact_rejection": 0.7869198312236287,
    "mean_predicted_labels_on_zero_gold": 0.45569620253164556,
    "hierarchy_violation_rate": 0.0,
    "FUNCTION_advisory_macro_f1": 0.0,
    "sample_f1": 0.5558,
    "jaccard": 0.5426,
    "gate_pass": False,
    "QUALIFICATION_DISPOSITION": "V6_CORE_QUALIFICATION_FAIL",
    "RELEASE_OUTCOME": "V6_CORE_RELEASE_CANDIDATE_REJECTED",
    "failure_class": "MIXED_CORE_GENERALIZATION_FAILURE",
    "evaluation_spent": True,
    "qualification_model_executions": 1,
}

CORE_REP_TO_QUAL_RETENTION = {
    "rep_core_system_macro_f1": CORE_WITNESS_REP_V3["core_system_macro_f1"],
    "qual_core_system_macro_f1": CORE_QUAL_METRICS["core_system_macro_f1"],
    "absolute_degradation": 0.25407027087471007,
    "relative_retention": 0.27083568666627783,
    "band": "SEVERE_GENERALIZATION_DROP",
    "DOMAIN_relative_retention": 0.4008973547804467,
    "MEDIATION_relative_retention": 0.1359570661896243,
    "NONE_exact_relative_retention": 0.8625663068843271,
}

# Historical fresh QUAL failures (all EVALUATION_SPENT).
SPENT_QUALIFICATION_SURFACES = (
    {
        "id": "HYPERLEX_V5_PIPELINE_QUALIFICATION_001",
        "era": "V5",
        "disposition": "QUALIFICATION_FAIL",
        "diagnosis": "MIXED_SYSTEM_GENERALIZATION_FAILURE",
        "v5_role": "V5_RESEARCH_PROTOTYPE",
    },
    {
        "id": "HYPERLEX_V6_QUALIFICATION_002",
        "era": "V6",
        "disposition": "QUALIFICATION_FAIL",
        "diagnosis": "REPRESENTATIVE_VALIDATION_OVERFIT",
        "system_macro_f1": 0.1885,
    },
    {
        "id": "HYPERLEX_V6_QUALIFICATION_003",
        "era": "V6",
        "disposition": "QUALIFICATION_FAIL",
        "diagnosis": "MIXED_POSITIVE_SEMANTIC_GENERALIZATION_FAILURE",
    },
    {
        "id": QUAL_CORE_ID,
        "era": "V6_CORE",
        "disposition": "V6_CORE_QUALIFICATION_FAIL",
        "diagnosis": "MIXED_CORE_GENERALIZATION_FAILURE",
        "core_system_macro_f1": CORE_QUAL_METRICS["core_system_macro_f1"],
        "retention_band": "SEVERE_GENERALIZATION_DROP",
    },
)

# Canonical capability table — Workstream A.
CAPABILITY_BASELINE: dict[str, dict[str, Any]] = {
    "hierarchical_multi_label_ontology": {
        "grade": "PROVEN",
        "evidence": (
            "Human ontology settlement; flat family ontology structurally unsound; "
            "V6 hierarchical multi-label is the settled semantic direction."
        ),
        "era": "V6",
    },
    "gold_identifiability_requirement": {
        "grade": "PROVEN",
        "evidence": (
            "V5 SHORT_ATOM NONE local repair; CORE QUAL gold stable "
            "(mean_core_jaccard=1.0). Identifiability is necessary."
        ),
        "era": "V5+V6",
    },
    "natural_observed_representative_data_requirement": {
        "grade": "PROVEN",
        "evidence": (
            "Positive-only / diagnostic surfaces produced misleading optimism "
            "(REP usable 0.43 vs QUAL 0.19); natural OBSERVED required."
        ),
        "era": "V5+V6",
    },
    "frozen_semantic_encoder_superiority_vs_hyperlex_modernbert": {
        "grade": "PROVEN",
        "evidence": (
            "MPNet zero-shot 0.206 > ModernBERT control 0.162; "
            "MSMARCO frozen nonlinear REP 0.443; PEFT/full FT not justified."
        ),
        "era": "V6",
    },
    "encoder_fine_tuning_justification": {
        "grade": "DISPROVEN_FOR_CURRENT_FORMULATION",
        "evidence": (
            "Full FT and PEFT failed to beat stronger frozen semantic priors; "
            "encoder_trainable_parameters=0 on core package."
        ),
        "era": "V6",
    },
    "explicit_none_rejection_gate": {
        "grade": "SUPPORTED_BUT_LIMITED",
        "evidence": (
            "REP zero-FP 0.088 / exact 0.912 after learned ANY_LABEL gate; "
            "CORE QUAL NONE exact retention ≈0.86 (best axis retention) but "
            "still missed QUAL floors (exact 0.787 < 0.80; FP 0.213 > 0.20)."
        ),
        "era": "V6",
    },
    "domain_text_only_final_labels": {
        "grade": "DISPROVEN_FOR_CURRENT_FORMULATION",
        "evidence": (
            "REP DOMAIN macro 0.355 → QUAL 0.142 (retention ≈0.40); "
            "fails release floors after hardening."
        ),
        "era": "V6_CORE",
    },
    "mediation_text_only_final_labels": {
        "grade": "DISPROVEN_FOR_CURRENT_FORMULATION",
        "evidence": (
            "REP MEDIATION macro 0.342 → QUAL 0.047 (retention ≈0.14); "
            "collapse on fresh operating text."
        ),
        "era": "V6_CORE",
    },
    "function_as_required_text_only_output": {
        "grade": "DISPROVEN_FOR_CURRENT_FORMULATION",
        "evidence": (
            "TEXT_SIGNAL_CEILING ≈0.30; pragmatic objective NOT_SUPPORTED; "
            "product disposition FUNCTION_RETAIN_OPTIONAL / ADVISORY_ONLY."
        ),
        "era": "V6",
    },
    "function_as_advisory_or_contextual": {
        "grade": "SUPPORTED_BUT_LIMITED",
        "evidence": (
            "Human-coherent labels; high context dependence; retained as "
            "advisory/research/contextual enrichment only."
        ),
        "era": "V6",
    },
    "memetic_form_product_output": {
        "grade": "DISPROVEN_FOR_CURRENT_FORMULATION",
        "evidence": "Very high FP cost; RESEARCH_ONLY.",
        "era": "V6",
    },
    "v5_flat_family_classification_pipeline": {
        "grade": "DISPROVEN_FOR_CURRENT_FORMULATION",
        "evidence": (
            "V5 QUAL FAIL; ontology not reliably separable; "
            "V5_RESEARCH_PROTOTYPE disposition."
        ),
        "era": "V5",
    },
    "v6_core_production_classifier": {
        "grade": "DISPROVEN_FOR_CURRENT_FORMULATION",
        "evidence": (
            "CORE QUAL FAIL: core macro-F1 0.094 < 0.30; "
            "SEVERE_GENERALIZATION_DROP vs REP_V3; RC REJECTED."
        ),
        "era": "V6_CORE",
    },
    "development_performance_predicts_operating_performance": {
        "grade": "DISPROVEN_FOR_CURRENT_FORMULATION",
        "evidence": (
            "Repeated fresh QUAL failures across V5 and V6; "
            "REP→QUAL relative retention 0.27 on core package."
        ),
        "era": "V5+V6",
    },
    "representative_validation_role_when_unfiltered": {
        "grade": "SUPPORTED_BUT_LIMITED",
        "evidence": (
            "Unfiltered REP repaired positive-only optimism and exposed NONE "
            "failure; still did not predict QUAL magnitude (shape yes, level no)."
        ),
        "era": "V6",
    },
    "semantic_representation_and_neighborhood_signals": {
        "grade": "SUPPORTED_BUT_LIMITED",
        "evidence": (
            "Frozen semantic embeddings recover axis signal above ModernBERT; "
            "geometry preserved; candidates/margins more stable than hard labels "
            "across redistribution; not release-qualified as final judgments."
        ),
        "era": "V6",
    },
    "distribution_shift_and_ontology_diagnostics": {
        "grade": "SUPPORTED_BUT_LIMITED",
        "evidence": (
            "Separability audits, source/length shift detection, and ontology "
            "diagnostics repeatedly explained QUAL failures; strongest research "
            "instrument role."
        ),
        "era": "V5+V6",
    },
    "contextual_semantic_reasoning_as_final_judge": {
        "grade": "UNRESOLVED",
        "evidence": (
            "FUNCTION and some mediation judgments require context; no fresh "
            "qualified contextual reasoner exists. Deferred as parallel research "
            "track — not a V6 core rescue."
        ),
        "era": "V6+",
    },
    "hybrid_representation_plus_external_verifier": {
        "grade": "UNRESOLVED",
        "evidence": (
            "Architecturally plausible (Hyperlex candidates → contextual verifier) "
            "but no verifier package has passed representative + fresh QUAL."
        ),
        "era": "future",
    },
    "head_threshold_seed_optimizer_microcycles": {
        "grade": "DISPROVEN_FOR_CURRENT_FORMULATION",
        "evidence": (
            "Local gains repeatedly failed global QUAL; program forbids further "
            "micro-cycles without a material task-formulation change."
        ),
        "era": "V5+V6",
    },
}


def grade_summary() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {g: [] for g in CAPABILITY_GRADES}
    for name, row in CAPABILITY_BASELINE.items():
        out[str(row["grade"])].append(name)
    return out


# ---------------------------------------------------------------------------
# Product contract (Workstream B)
# ---------------------------------------------------------------------------

PRODUCT_INTERFACES = (
    "embedding",
    "semantic_candidates",
    "nearest_semantic_concepts",
    "confidence_margin",
    "ambiguity_signal",
    "distribution_distance_signal",
    "representation_drift_signal",
    "ontology_neighborhood_evidence",
    "evidence_abstention_signal",
)


def product_requirement_table() -> list[dict[str, Any]]:
    """Per-capability consumer / decision / failure / input analysis."""
    return [
        {
            "capability": "final_domain_label",
            "consumer": "downstream routers / analysts expecting hard DOMAIN",
            "downstream_decision": "route or filter by domain",
            "cost_if_wrong": "high — silent misrouting",
            "omission_preferable": True,
            "isolated_text_sufficient": False,
            "context_required": "often document/entity",
            "output_mode": "probabilistic_advisory_candidates",
            "useful": True,
            "evidence_supported_as_required": False,
            "product_placement": "ADVISORY_CANDIDATES",
        },
        {
            "capability": "final_mediation_label",
            "consumer": "register / mediation analytics",
            "downstream_decision": "tag internet-register mediation",
            "cost_if_wrong": "high — QUAL collapse (retention ≈0.14)",
            "omission_preferable": True,
            "isolated_text_sufficient": False,
            "context_required": "often conversational",
            "output_mode": "probabilistic_advisory_candidates",
            "useful": True,
            "evidence_supported_as_required": False,
            "product_placement": "ADVISORY_CANDIDATES",
        },
        {
            "capability": "final_function_label",
            "consumer": "stance / intimacy / conflict studies",
            "downstream_decision": "pragmatic force labeling",
            "cost_if_wrong": "very high (esp. memetic FP)",
            "omission_preferable": True,
            "isolated_text_sufficient": False,
            "context_required": True,
            "output_mode": "advisory_or_contextual_only",
            "useful": True,
            "evidence_supported_as_required": False,
            "product_placement": "RESEARCH_OR_CONTEXTUAL",
        },
        {
            "capability": "evidence_abstention_none_signal",
            "consumer": "ingest gates / observability",
            "downstream_decision": "abstain vs admit for semantic labeling",
            "cost_if_wrong": "medium — FP admits noise; FN drops recall",
            "omission_preferable": False,
            "isolated_text_sufficient": "partial",
            "context_required": False,
            "output_mode": "probabilistic_with_margin",
            "useful": True,
            "evidence_supported_as_required": True,
            "product_placement": "REQUIRED_SIGNAL",
            "note": "Most stable axis across CORE QUAL; still imperfect floors.",
        },
        {
            "capability": "frozen_semantic_embedding",
            "consumer": "Noesis / retrieval / neighborhood tools / drift monitors",
            "downstream_decision": "similarity, clustering, candidate generation",
            "cost_if_wrong": "low-medium — continuous space, no hard mislabel",
            "omission_preferable": False,
            "isolated_text_sufficient": True,
            "context_required": False,
            "output_mode": "deterministic_given_encoder_pin",
            "useful": True,
            "evidence_supported_as_required": True,
            "product_placement": "REQUIRED_OUTPUT",
        },
        {
            "capability": "semantic_candidates_and_margins",
            "consumer": "human review / contextual reasoners / hybrid verifiers",
            "downstream_decision": "narrow search space; never finalize alone",
            "cost_if_wrong": "medium if treated as final; low if ranked candidates",
            "omission_preferable": False,
            "isolated_text_sufficient": True,
            "context_required": False,
            "output_mode": "ranked_probabilistic",
            "useful": True,
            "evidence_supported_as_required": True,
            "product_placement": "REQUIRED_OUTPUT",
        },
        {
            "capability": "ambiguity_distribution_drift_diagnostics",
            "consumer": "Trutina / Semion / ops / ontology maintainers",
            "downstream_decision": "detect shift, separability failure, OOD",
            "cost_if_wrong": "low — diagnostic",
            "omission_preferable": False,
            "isolated_text_sufficient": True,
            "context_required": False,
            "output_mode": "explanatory_measurement",
            "useful": True,
            "evidence_supported_as_required": True,
            "product_placement": "REQUIRED_OUTPUT",
        },
    ]


def minimum_viable_product_contract() -> dict[str, Any]:
    """USEFUL ∧ EVIDENCE-SUPPORTED capabilities only."""
    required = [
        r["capability"]
        for r in product_requirement_table()
        if r["useful"] and r["evidence_supported_as_required"]
    ]
    advisory = [
        r["capability"]
        for r in product_requirement_table()
        if r["useful"] and not r["evidence_supported_as_required"]
    ]
    return {
        "product_name": "Hyperlex Semantic Representation & Measurement Layer",
        "product_role": "HYPERLEX_REPRESENTATION_AND_MEASUREMENT_LAYER",
        "required_outputs": required,
        "advisory_outputs": advisory,
        "research_only": [
            "function.memetic_form",
            "final_hard_multi_label_classifier_release",
            "v5_flat_family_pipeline",
        ],
        "deprecated_as_required_product_outputs": [
            "final_domain_label",
            "final_mediation_label",
            "final_function_label",
        ],
        "interfaces": list(PRODUCT_INTERFACES),
        "encoder_policy": {
            "family": "frozen_sentence_or_retrieval_embedding",
            "selected_reference": SELECTED_ENCODER_MODEL_ID,
            "revision_reference": SELECTED_ENCODER_REVISION,
            "fine_tuning": "not_justified",
            "hyperlex_modernbert_best_role": "HISTORICAL_CONTROL_ONLY",
            "MODEL_WIDE_BEST_sha256": MODEL_WIDE_BEST_SHA256,
        },
        "ontology_role": {
            "HYPERLEX_V6_FAMILY_ONTOLOGY_V1_FINAL": (
                "canonical concept space for candidates and diagnostics"
            ),
            "not_a_mandatory_classifier_output_checklist": True,
        },
        "determinism": {
            "embedding": "deterministic_given_pin",
            "candidates": "deterministic_given_pin_and_thresholds",
            "final_labels": "not_a_product_guarantee",
        },
        "failure_policy": {
            "prefer_abstention_over_false_emission": True,
            "hard_labels_must_not_block_downstream_without_human_or_verifier": True,
        },
        "useful_and_evidence_supported_only": True,
    }


# ---------------------------------------------------------------------------
# Task formulation (Workstream C)
# ---------------------------------------------------------------------------

CENTRAL_ARCHITECTURAL_ANSWER = (
    "Hyperlex is failing as a production classifier because final semantic "
    "judgment is not the right job for a lightweight text-only classifier under "
    "the operating distribution — not because the latest head/threshold/seed was "
    "wrong. Frozen semantic representations, abstention signals, candidates, and "
    "diagnostics are the evidence-supported job."
)


def task_formulation_decision() -> dict[str, Any]:
    return {
        "central_question": (
            "Is Hyperlex failing because we have not found the right classifier, "
            "or because final semantic judgment is not the right job for a "
            "lightweight text-only classifier?"
        ),
        "answer": CENTRAL_ARCHITECTURAL_ANSWER,
        "rejected_primary_formulation": "classification",
        "selected_primary_formulation": "representation_only_output",
        "secondary_formulations": [
            "candidate_generation",
            "abstaining_decision_system",
            "semantic_matching",
        ],
        "deferred_formulations": [
            "contextual_reasoning",
            "retrieval_plus_verification",
        ],
        "comparison": [
            {
                "formulation": "classification",
                "fit": "poor",
                "reason": "four consecutive fresh QUAL failures; SEVERE_GENERALIZATION_DROP",
            },
            {
                "formulation": "semantic_matching",
                "fit": "partial",
                "reason": "frozen embedding matching beats ModernBERT; still weak as hard labels",
            },
            {
                "formulation": "candidate_generation",
                "fit": "good",
                "reason": "narrows space for humans/verifiers without claiming finality",
            },
            {
                "formulation": "abstaining_decision_system",
                "fit": "good_for_evidence_gate",
                "reason": "NONE/evidence signal most stable across QUAL",
            },
            {
                "formulation": "representation_only_output",
                "fit": "best_primary",
                "reason": "embeddings + diagnostics generalize better than final labels",
            },
            {
                "formulation": "contextual_reasoning",
                "fit": "deferred",
                "reason": "needed for FUNCTION/pragmatics; not justified as V6 classifier rescue",
            },
            {
                "formulation": "retrieval_plus_verification",
                "fit": "deferred_hybrid",
                "reason": "plausible future hybrid; no qualified verifier yet",
            },
        ],
    }


# ---------------------------------------------------------------------------
# Evaluation architecture (Workstream F)
# ---------------------------------------------------------------------------


def evaluation_architecture_contract() -> dict[str, Any]:
    return {
        "stages": {
            "TRAIN": {
                "role": "fit representation probes / gates / candidate scorers only",
                "may_tune": True,
            },
            "DEV_SELECTION": {
                "role": "select thresholds and candidates among TRAIN-admitted variants",
                "may_tune": True,
                "not_release_binding": True,
            },
            "REPRESENTATIVE_VALIDATION": {
                "role": (
                    "operating-traffic mirror; must include NONE/NO_EVIDENCE mass; "
                    "never silently filter to easier positive-only subsets"
                ),
                "may_tune": False,
                "release_witness": True,
                "forbidden_filters": [
                    "usable_positive_only",
                    "drop_zero_label",
                    "diagnostic_contrast_pairing_as_operating_proxy",
                ],
            },
            "FRESH_QUALIFICATION": {
                "role": "blind one-shot product question; seal before score; spend forever",
                "may_tune": False,
                "retries_without_material_hypothesis_change": False,
            },
        },
        "required_candidate_report": [
            "development_performance",
            "representative_performance",
            "generalization_gap",
            "source_sensitivity",
            "zero_label_behavior",
            "positive_semantic_behavior",
            "relevant_subgroup_behavior",
        ],
        "advancement_to_qualification_requires": [
            "stable_representative_validation",
            "no_major_source_or_distribution_collapse",
            "acceptable_rejection_abstention_behavior",
            "meaningful_improvement_over_best_evidence_backed_baseline",
            "plausible_product_role",
            "no_dependence_on_development_only_artifact",
        ],
        "spent_surfaces_permanently_excluded": [
            s["id"] for s in SPENT_QUALIFICATION_SURFACES
        ],
        "predictiveness_standard": (
            "Representative validation must predict the *shape* of fresh "
            "qualification (axis ordering, NONE vs positive failure modes), "
            "even if absolute scores differ."
        ),
        "classifier_fresh_qualification_status": {
            "core_package": "EVALUATION_SPENT_FAIL",
            "further_classifier_qual_without_task_reformulation": "FORBIDDEN",
        },
    }


# ---------------------------------------------------------------------------
# Architecture direction (Workstreams D, E, G)
# ---------------------------------------------------------------------------


def architecture_direction() -> dict[str, Any]:
    return {
        "families_authorized": [
            {
                "family": "representation_measurement_layer",
                "status": "SELECTED_PRIMARY",
                "components": [
                    "frozen_semantic_encoder",
                    "evidence_abstention_gate_as_signal",
                    "ontology_neighborhood_candidate_generator",
                    "ambiguity_margin_drift_diagnostics",
                ],
            }
        ],
        "families_rejected": [
            {
                "family": "text_only_final_label_classifier",
                "status": "REJECTED",
                "reason": "CORE QUAL FAIL + repeated V5/V6 QUAL failures",
            },
            {
                "family": "head_width_seed_threshold_optimizer_variants",
                "status": "REJECTED",
                "reason": "not a material task-formulation change",
            },
            {
                "family": "hyperlex_modernbert_finetune",
                "status": "REJECTED",
                "reason": "frozen semantic encoders dominate; FT not justified",
            },
        ],
        "families_deferred": [
            {
                "family": "contextual_semantic_reasoner",
                "status": "DEFERRED_PARALLEL_RESEARCH",
                "reason": (
                    "Justified for FUNCTION/pragmatics when context is available; "
                    "not a substitute rescue of the text-only classifier. "
                    "Requires separate product contract and fresh QUAL."
                ),
                "blocker_for_this_settlement": (
                    "No GPU / no qualified contextual package in-session; "
                    "final text-only judgments lack product value → D not required "
                    "to settle primary disposition."
                ),
            },
            {
                "family": "hybrid_representation_plus_verifier",
                "status": "DEFERRED",
                "reason": "attractive follow-on once a verifier exists",
            },
        ],
        "representation_strategy": {
            "encoder": "frozen sentence/retrieval embedding (MSMARCO/MPNet/BGE class)",
            "heads": "optional shallow probes for candidates only — never release-binding hard labels",
            "hierarchy": "ontology constraints for candidate legality, not forced emission",
        },
        "contextual_reasoning_strategy": {
            "authorized_now": False,
            "when_justified": (
                "Downstream needs final FUNCTION/pragmatic judgments with "
                "document/conversation context; Hyperlex supplies candidates only."
            ),
        },
    }


# ---------------------------------------------------------------------------
# Disposition (Workstreams H–J)
# ---------------------------------------------------------------------------


def classify_program_disposition(audit: Mapping[str, Any]) -> dict[str, Any]:
    """Select exactly one primary disposition from settled evidence flags."""
    core_qual_pass = bool(audit.get("core_qual_pass"))
    contextual_qual_pass = bool(audit.get("contextual_qual_pass"))
    hybrid_qual_pass = bool(audit.get("hybrid_qual_pass"))
    representation_more_stable = bool(audit.get("representation_more_stable_than_labels"))
    scientific_value_remains = bool(audit.get("scientific_value_remains", True))
    classification_still_justified = bool(
        audit.get("classification_work_still_justified", False)
    )

    if core_qual_pass:
        disposition = "HYPERLEX_PRODUCTION_CLASSIFIER"
        release = "RELEASE_AUTHORIZED"
        rationale = "Required semantic outputs survived fresh qualification."
    elif contextual_qual_pass:
        disposition = "HYPERLEX_CONTEXTUAL_SEMANTIC_REASONER"
        release = "RELEASE_AUTHORIZED"
        rationale = "Final judgments require and pass contextual reasoning QUAL."
    elif hybrid_qual_pass:
        disposition = "HYPERLEX_HYBRID_SYSTEM"
        release = "RELEASE_AUTHORIZED"
        rationale = "Representation + contextual verifier passed product QUAL."
    elif representation_more_stable and scientific_value_remains:
        disposition = "HYPERLEX_REPRESENTATION_AND_MEASUREMENT_LAYER"
        release = "SHADOW_INSTRUMENT_ONLY"
        rationale = (
            "Representations, candidates, abstention, and diagnostics are the "
            "strongest evidence-supported product role; final-label classifier "
            "is conclusively rejected."
        )
    elif scientific_value_remains and not classification_still_justified:
        disposition = "HYPERLEX_RESEARCH_PLATFORM"
        release = "RESEARCH_ONLY"
        rationale = "Scientific/evaluation value remains; product inference unsupported."
    else:
        disposition = "HYPERLEX_CLASSIFICATION_PROGRAM_ARCHIVED"
        release = "REJECTED_NOT_RELEASE_ELIGIBLE"
        rationale = "Continued classification work is not justified."

    return {
        "PRIMARY_DISPOSITION": disposition,
        "RELEASE_STATUS": release,
        "HUB_PUBLISH_AUTHORIZED": False,
        "CLASSIFIER_RELEASE_ELIGIBLE": False,
        "rationale": rationale,
        "classifier_candidate_result": {
            "package": CORE_PACKAGE_ID,
            "qualification": QUAL_CORE_ID,
            "result": "CONCLUSIVELY_REJECTED",
            "QUALIFICATION_DISPOSITION": CORE_QUAL_METRICS["QUALIFICATION_DISPOSITION"],
            "core_system_macro_f1": CORE_QUAL_METRICS["core_system_macro_f1"],
            "retention_band": CORE_REP_TO_QUAL_RETENTION["band"],
        },
        "representation_layer_status": {
            "role": "PRIMARY_PRODUCT_DIRECTION",
            "release": release,
            "interfaces": list(PRODUCT_INTERFACES),
            "fresh_label_qualification": "not_applicable_final_labels_rejected",
            "next_qualification_if_any": (
                "representation_signal_stability_contract_only — "
                "requires material new hypothesis, not classifier retry"
            ),
        },
        "NEXT_ACTION": "EXECUTE_REPRESENTATION_MEASUREMENT_ROADMAP",
    }


def settled_audit_from_evidence() -> dict[str, Any]:
    """Frozen audit flags derived from settled V5/V6 receipts (no retrain)."""
    none_ret = CORE_REP_TO_QUAL_RETENTION["NONE_exact_relative_retention"]
    core_ret = CORE_REP_TO_QUAL_RETENTION["relative_retention"]
    return {
        "core_qual_pass": False,
        "contextual_qual_pass": False,
        "hybrid_qual_pass": False,
        "representation_more_stable_than_labels": none_ret > core_ret * 2.0,
        "scientific_value_remains": True,
        "classification_work_still_justified": False,
        "none_vs_core_retention": {
            "NONE_exact_relative_retention": none_ret,
            "core_relative_retention": core_ret,
        },
        "spent_qualification_count": len(SPENT_QUALIFICATION_SURFACES),
        "function_product_parent": FUNCTION_PRODUCT_EXPERIMENT,
        "core_package_sha256_pin": CORE_PACKAGE_SHA256_PIN,
    }


def ecosystem_integration() -> dict[str, Any]:
    return {
        "Noesis": {
            "role": "consume embeddings + candidates; do not treat Hyperlex hard labels as truth",
            "pairwise_qualification": "unblocked_from_classifier_dependency; use representation contract",
        },
        "Abraxas": {
            "role": "experiment coordination may reference Hyperlex diagnostics; no rune/forecast coupling",
        },
        "Trutina": {
            "role": "consume distribution-distance / drift / separability signals",
        },
        "Semion": {
            "role": "ontology-neighborhood and ambiguity observability",
        },
        "Hyperlexical_structure_pin_morph78": {
            "role": "separate structure-encoder product track; not the V6 classifier",
            "note": "morph78 BEST remains independent of classification disposition",
        },
        "downstream_contextual_reasoners": {
            "role": "may use Hyperlex candidates as search-space narrowing only",
        },
    }


def deprecated_paths() -> list[str]:
    return [
        "V5 flat-family production classifier",
        "V6 three-axis required FUNCTION release path",
        "V6 core DOMAIN+MEDIATION hard-label release path",
        "ModernBERT Hyperlex BEST as default semantic backbone",
        "encoder fine-tuning for V6 classification",
        "positive-only usable() representative validation",
        "threshold/seed/optimizer/head-width micro-cycles without task reformulation",
        "rescoring or training on spent QUAL-001/002/003/CORE surfaces",
        "treating diagnostic contrast surfaces as operating validation",
        "mandatory emission of every ontology concept as classifier output",
    ]


def follow_on_roadmap() -> list[dict[str, str]]:
    return [
        {
            "step": "1",
            "action": "Ship frozen-encoder embedding + candidate API under SHADOW_INSTRUMENT_ONLY",
            "blocks_on": "none",
        },
        {
            "step": "2",
            "action": "Instrument NONE/evidence, margin, ambiguity, drift on live OBSERVED traffic",
            "blocks_on": "step_1",
        },
        {
            "step": "3",
            "action": "Define representation-signal stability QUAL (not label F1 floors)",
            "blocks_on": "representative_traffic_mirror",
        },
        {
            "step": "4",
            "action": "Optional hybrid: Hyperlex candidates → external contextual verifier",
            "blocks_on": "verifier_owner_and_fresh_surface",
        },
        {
            "step": "5",
            "action": "Keep FUNCTION/pragmatics as contextual research; never re-mandate text-only",
            "blocks_on": "none",
        },
        {
            "step": "6",
            "action": "Do not open another classifier QUAL without material task reformulation",
            "blocks_on": "n/a_forbidden",
        },
    ]


def program_settlement_contract() -> dict[str, Any]:
    return {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "SCHEMA": SCHEMA,
        "capability_grades": CAPABILITY_GRADES,
        "capability_baseline": CAPABILITY_BASELINE,
        "grade_summary": grade_summary(),
        "spent_qualification_surfaces": list(SPENT_QUALIFICATION_SURFACES),
        "core_qual_metrics": CORE_QUAL_METRICS,
        "core_rep_to_qual_retention": CORE_REP_TO_QUAL_RETENTION,
        "product_requirement_table": product_requirement_table(),
        "minimum_viable_product_contract": minimum_viable_product_contract(),
        "task_formulation": task_formulation_decision(),
        "evaluation_architecture": evaluation_architecture_contract(),
        "architecture_direction": architecture_direction(),
        "ecosystem_integration": ecosystem_integration(),
        "deprecated_paths": deprecated_paths(),
        "follow_on_roadmap": follow_on_roadmap(),
        "primary_dispositions": list(PRIMARY_DISPOSITIONS),
        "forbidden": [
            "train_another_classifier_head",
            "threshold_seed_optimizer_sweep",
            "rescore_spent_QUAL",
            "lower_QUAL_gates_post_hoc",
            "reuse_spent_QUAL_rows_for_training_or_selection",
            "promote_core_classifier_to_release",
            "reopen_flat_family_ontology",
            "mandate_FUNCTION_as_required_text_only_output",
        ],
        "stop_conditions_for_human": [
            "data_integrity_violation",
            "safety_or_dual_use_escalation",
            "product_contract_owner_override",
            "scientific_contradiction_of_settled_baseline",
        ],
    }


def build_program_settlement_receipt(
    audit: Mapping[str, Any] | None = None,
    *,
    sealed_at: str,
) -> dict[str, Any]:
    audit_resolved = dict(audit or settled_audit_from_evidence())
    disposition = classify_program_disposition(audit_resolved)
    contract = program_settlement_contract()
    body = {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "SCHEMA": SCHEMA,
        "sealed_at": sealed_at,
        "audit": audit_resolved,
        "disposition": disposition,
        "grade_summary": contract["grade_summary"],
        "minimum_viable_product_contract": contract[
            "minimum_viable_product_contract"
        ],
        "task_formulation": contract["task_formulation"],
        "evaluation_architecture": {
            "stages": list(contract["evaluation_architecture"]["stages"].keys()),
            "spent_surfaces": contract["evaluation_architecture"][
                "spent_surfaces_permanently_excluded"
            ],
            "classifier_fresh_qualification_status": contract[
                "evaluation_architecture"
            ]["classifier_fresh_qualification_status"],
        },
        "architecture_direction": {
            "selected": [
                f["family"]
                for f in contract["architecture_direction"]["families_authorized"]
            ],
            "rejected": [
                f["family"]
                for f in contract["architecture_direction"]["families_rejected"]
            ],
            "deferred": [
                f["family"]
                for f in contract["architecture_direction"]["families_deferred"]
            ],
        },
        "axis_roles": {
            "evidence_NONE": "REQUIRED_SIGNAL",
            "DOMAIN": "ADVISORY_CANDIDATES_NOT_HARD_RELEASE",
            "MEDIATION": "ADVISORY_CANDIDATES_NOT_HARD_RELEASE",
            "FUNCTION": "ADVISORY_OR_CONTEXTUAL_RESEARCH",
            "memetic_form": "RESEARCH_ONLY",
        },
        "core_qual_result": CORE_QUAL_METRICS,
        "retention": CORE_REP_TO_QUAL_RETENTION,
        "deprecated_paths": deprecated_paths(),
        "ecosystem_integration": ecosystem_integration(),
        "follow_on_roadmap": follow_on_roadmap(),
        "MODEL_WIDE_BEST_MUTATED": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "CLASSIFIER_RETRAINED": False,
        "SPENT_QUAL_RESCORED": False,
        "GATES_LOWERED_POST_HOC": False,
    }
    digest = sha256_text(canonical_json(body))
    body["SYSTEM_PROGRAM_SETTLEMENT_RECEIPT_SHA256"] = digest
    return body

