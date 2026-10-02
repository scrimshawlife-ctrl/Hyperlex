"""REASSESS_V6_FUNCTION_PRODUCT_REQUIREMENT — contracts.

Product-level decision: whether FUNCTION remains a required Hyperlex V6
output. Read-only. No new function model, no encoder/NONE/DOMAIN/MEDIATION/
ontology mutation, no QUAL rescoring.
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
from .classification_v6_label_migration import FUNCTION_VOCAB
from .classification_v6_operating_pipeline_harden import (
    OPERATING_QUALIFICATION_GATES,
    WITNESS_GATE_THRESHOLD,
)
from .classification_v6_pragmatic_function_objective import (
    EXPERIMENT_ID as PARENT_PRAG_EXPERIMENT,
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
    SELECTED_ENCODER_MODEL_ID,
    SELECTED_ENCODER_REVISION,
)

PHASE_RULE = "REASSESS_V6_FUNCTION_PRODUCT_REQUIREMENT"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-FUNCTION-PRODUCT-REQUIREMENT-001"
SCHEMA = "hyperlex.classification.v6.function_product_requirement.v1"

PARENT = {
    "FUNCTION_TASK_SIGNAL": "FUNCTION_TASK_SIGNAL_PARTIAL",
    "CEILING_CLASS": "TEXT_SIGNAL_CEILING",
    "PRAGMATIC_OBJECTIVE": "V6_PRAGMATIC_OBJECTIVE_NOT_SUPPORTED",
    "parent_pragmatic_experiment": PARENT_PRAG_EXPERIMENT,
    "direct_FUNCTION_baseline": BASELINE_REP_V3["FUNCTION_macro_f1"],
    "independent_verifier_FUNCTION": 0.29381283709203987,
    "hybrid_FUNCTION": 0.30579399645778493,
    "primitive_macro_f1": 0.1884559297606857,
    "derived_FUNCTION": 0.19764682696097755,
    "primitive_cue_recovery_lift": 0.012759170653907498,
}

AXIS_DISPOSITIONS = (
    "KEEP_REQUIRED",
    "KEEP_OPTIONAL",
    "KEEP_RESEARCH_ONLY",
    "DEPRECATE_FROM_PRODUCT",
)

PLACEMENT_OPTIONS = (
    "DOWNSTREAM_REASONING_ONLY",
    "CONTEXTUAL_ENRICHMENT",
    "HUMAN_ANNOTATION_ONLY",
)

PRODUCT_DISPOSITIONS = (
    "FUNCTION_RETAIN_REQUIRED",
    "FUNCTION_RETAIN_OPTIONAL",
    "FUNCTION_MOVE_TO_CONTEXTUAL_LAYER",
    "FUNCTION_DEPRECATE_FROM_V6_PRODUCT",
)

NEXT_ACTIONS = (
    "HARDEN_V6_CORE_PRODUCT_WITHOUT_REQUIRED_FUNCTION",
    "DESIGN_CONTEXTUAL_FUNCTION_ENRICHMENT_TRACK",
    "REDEFINE_FUNCTION_INPUT_CONTRACT",
)

CONTRACT_ALTERNATIVES = (
    "A_KEEP_FUNCTION_MANDATORY",
    "B_MAKE_FUNCTION_OPTIONAL_BEST_EFFORT",
    "C_MOVE_FUNCTION_TO_CONTEXTUAL_REASONING",
    "D_REMOVE_FUNCTION_FROM_V6_PRODUCT_SCOPE",
)

# Settled per-function forensic table (REP_V3 / task-signal / redesign).
PER_FUNCTION_EVIDENCE: dict[str, dict[str, Any]] = {
    "function.conflictive_force": {
        "signal_class": "CONTEXT_SENSITIVE",
        "old_head_f1": 0.3214285714285714,
        "independent_f1": 0.32592592592592595,
        "hybrid_f1": 0.25225225225225223,
        "baseline_precision": 0.36,
        "baseline_recall": 0.2903225806451613,
        "independent_precision": 0.3013698630136986,
        "explicit_lexical_share": 0.0967741935483871,
        "pragmatic_or_context_share": 0.8225806451612904,
        "consensus_fail_share": 0.6774193548387096,
        "rep_support": 62,
        "downstream_utility": (
            "Useful for hostility/combat framing in memetic/conflict studies; "
            "not required for domain routing or NONE rejection."
        ),
        "cost_of_false_positive": "high",
        "cost_of_false_negative": "medium",
        "context_dependence": "high",
        "substitutable_by_domain_mediation": (
            "Partially: conflict domains exist, but hostility force is not a domain."
        ),
    },
    "function.evaluative_stance": {
        "signal_class": "CONTEXT_SENSITIVE",
        "old_head_f1": 0.28915662650602403,
        "independent_f1": 0.23880597014925375,
        "hybrid_f1": 0.27972027972027974,
        "baseline_precision": 0.375,
        "baseline_recall": 0.23529411764705882,
        "independent_precision": 0.1927710843373494,
        "explicit_lexical_share": 0.11764705882352941,
        "pragmatic_or_context_share": 0.8823529411764706,
        "consensus_fail_share": 0.6470588235294118,
        "rep_support": 51,
        "downstream_utility": (
            "Core to pejoration/prestige analysis; often needs pragmatic inference "
            "beyond the isolated sentence."
        ),
        "cost_of_false_positive": "high",
        "cost_of_false_negative": "medium",
        "context_dependence": "very_high",
        "substitutable_by_domain_mediation": (
            "No: stance is orthogonal to domain/mediation."
        ),
    },
    "function.memetic_form": {
        "signal_class": "CONTEXT_SENSITIVE",
        "old_head_f1": 0.26506024096385544,
        "independent_f1": 0.26168224299065423,
        "hybrid_f1": 0.38532110091743116,
        "baseline_precision": 0.2972972972972973,
        "baseline_recall": 0.2391304347826087,
        "independent_precision": 0.16666666666666666,
        "explicit_lexical_share": 0.13043478260869565,
        "pragmatic_or_context_share": 0.8260869565217391,
        "consensus_fail_share": 0.5,
        "rep_support": 46,
        "downstream_utility": (
            "Central to Hyperlex memetics research, but format identity usually "
            "needs discourse/template/world context."
        ),
        "cost_of_false_positive": "very_high",
        "cost_of_false_negative": "medium",
        "context_dependence": "very_high",
        "substitutable_by_domain_mediation": (
            "No: internet_register mediation ≠ memetic form."
        ),
    },
    "function.relational_intimacy": {
        "signal_class": "CONTEXT_SENSITIVE",
        "old_head_f1": 0.30985915492957744,
        "independent_f1": 0.3488372093023256,
        "hybrid_f1": 0.3058823529411765,
        "baseline_precision": 0.5,
        "baseline_recall": 0.22448979591836735,
        "independent_precision": 0.40540540540540543,
        "explicit_lexical_share": 0.20408163265306123,
        "pragmatic_or_context_share": 0.7959183673469388,
        "consensus_fail_share": 0.7346938775510204,
        "rep_support": 49,
        "downstream_utility": (
            "Useful for intimacy/relationship lexicon slices; comparatively "
            "best precision among the four when cues are explicit."
        ),
        "cost_of_false_positive": "high",
        "cost_of_false_negative": "medium",
        "context_dependence": "high",
        "substitutable_by_domain_mediation": (
            "No: intimacy is not encoded by domain/mediation alone."
        ),
    },
}

REJECTED_MICRO_FIXES = {
    "train_another_function_model": False,
    "change_encoder": False,
    "change_NONE_gate": False,
    "retrain_DOMAIN": False,
    "retrain_MEDIATION": False,
    "change_ontology": False,
    "rescore_QUAL": False,
}


def _hash(payload: Any) -> str:
    return sha256_text(canonical_json(payload))


def core_without_function_metrics(
    *,
    domain_macro: float,
    mediation_macro: float,
    zero_fp: float,
    zero_exact: float,
    positive_domain_macro: float | None = None,
    positive_mediation_macro: float | None = None,
    hierarchy_violation_rate: float = 0.0,
) -> dict[str, Any]:
    """Reconstruct V6 core quality excluding FUNCTION from system macro."""
    core_system = (float(domain_macro) + float(mediation_macro)) / 2.0
    if positive_domain_macro is not None and positive_mediation_macro is not None:
        pos_only = (float(positive_domain_macro) + float(positive_mediation_macro)) / 2.0
    else:
        pos_only = None
    return {
        "core_axes": ["domain", "mediation"],
        "DOMAIN_macro_f1": float(domain_macro),
        "MEDIATION_macro_f1": float(mediation_macro),
        "core_system_macro_f1": core_system,
        "positive_only_core_macro_f1": pos_only,
        "zero_label_false_positive_rate": float(zero_fp),
        "zero_label_exact_rejection": float(zero_exact),
        "hierarchy_violation_rate": float(hierarchy_violation_rate),
        "FUNCTION_excluded_from_system_macro": True,
        "vs_three_axis_system_macro_f1": BASELINE_REP_V3["system_macro_f1"],
        "core_vs_three_axis_delta": core_system - BASELINE_REP_V3["system_macro_f1"],
    }


def recommend_function_disposition(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Per-function product disposition from settled forensic evidence."""
    f1 = max(
        float(evidence.get("old_head_f1") or 0.0),
        float(evidence.get("independent_f1") or 0.0),
        float(evidence.get("hybrid_f1") or 0.0),
    )
    prec = float(
        evidence.get("baseline_precision")
        or evidence.get("independent_precision")
        or 0.0
    )
    prag = float(evidence.get("pragmatic_or_context_share") or 0.0)
    cons = float(evidence.get("consensus_fail_share") or 0.0)
    fp_cost = str(evidence.get("cost_of_false_positive") or "high")

    placement: list[str] = ["HUMAN_ANNOTATION_ONLY"]
    if prag >= 0.75 or cons >= 0.55:
        placement.append("CONTEXTUAL_ENRICHMENT")
    if prag >= 0.85:
        placement.append("DOWNSTREAM_REASONING_ONLY")

    if f1 >= 0.40 and prec >= 0.45 and prag < 0.55:
        disp = "KEEP_REQUIRED"
    elif prec >= 0.35 and f1 >= 0.28:
        disp = "KEEP_OPTIONAL"
    elif fp_cost == "very_high" and prec < 0.30:
        disp = "KEEP_RESEARCH_ONLY"
    else:
        disp = "KEEP_OPTIONAL"

    return {
        "disposition": disp,
        "placement": placement,
        "best_f1": f1,
        "best_precision": prec,
        "text_only_recoverability": (
            "low" if prag >= 0.75 or cons >= 0.55 else "moderate"
        ),
        "human_stability": "coherent_but_not_text_grounded",
        "model_ceiling_evidence": "~0.25–0.35 per-label F1 under frozen text encoder",
    }


def classify_product_disposition(audit: Mapping[str, Any]) -> dict[str, Any]:
    """Axis-level product disposition + NEXT_ACTION."""
    per = dict(audit.get("per_function_dispositions") or {})
    dispositions = [dict(v).get("disposition") for v in per.values()]
    n_required = sum(1 for d in dispositions if d == "KEEP_REQUIRED")
    n_optional = sum(1 for d in dispositions if d == "KEEP_OPTIONAL")
    n_research = sum(1 for d in dispositions if d == "KEEP_RESEARCH_ONLY")
    n_deprecate = sum(1 for d in dispositions if d == "DEPRECATE_FROM_PRODUCT")

    ceiling = audit.get("ceiling_class") or PARENT["CEILING_CLASS"]
    pragmatic = audit.get("pragmatic_outcome") or PARENT["PRAGMATIC_OBJECTIVE"]
    core = dict(audit.get("core_without_function") or {})
    core_system = float(core.get("core_system_macro_f1") or 0.0)
    none_ok = bool(audit.get("none_preserved", True))
    cue_lift = float(
        audit.get("primitive_cue_recovery_lift")
        or PARENT["primitive_cue_recovery_lift"]
    )
    baseline_fun = float(
        audit.get("baseline_FUNCTION_macro_f1") or PARENT["direct_FUNCTION_baseline"]
    )

    # Mandatory only if labels clear the text-only bar — they do not.
    if (
        n_required >= 3
        and baseline_fun >= 0.40
        and ceiling != "TEXT_SIGNAL_CEILING"
        and pragmatic != "V6_PRAGMATIC_OBJECTIVE_NOT_SUPPORTED"
    ):
        product = "FUNCTION_RETAIN_REQUIRED"
        next_action = "REDEFINE_FUNCTION_INPUT_CONTRACT"
        alternative = "A_KEEP_FUNCTION_MANDATORY"
        rationale = "text_only_ceiling_still_meets_downstream_need"
    elif n_deprecate >= 3 and n_optional == 0:
        product = "FUNCTION_DEPRECATE_FROM_V6_PRODUCT"
        next_action = "HARDEN_V6_CORE_PRODUCT_WITHOUT_REQUIRED_FUNCTION"
        alternative = "D_REMOVE_FUNCTION_FROM_V6_PRODUCT_SCOPE"
        rationale = "no_function_retains_product_utility"
    elif (
        cue_lift < 0.05
        and pragmatic == "V6_PRAGMATIC_OBJECTIVE_NOT_SUPPORTED"
        and all(
            "CONTEXTUAL_ENRICHMENT" in (dict(v).get("placement") or [])
            for v in per.values()
        )
        and audit.get("prefer_contextual_only")
    ):
        product = "FUNCTION_MOVE_TO_CONTEXTUAL_LAYER"
        next_action = "DESIGN_CONTEXTUAL_FUNCTION_ENRICHMENT_TRACK"
        alternative = "C_MOVE_FUNCTION_TO_CONTEXTUAL_REASONING"
        rationale = "reliable_function_requires_non_text_context"
    else:
        # Default settled path: optional/best-effort, core without required FUNCTION.
        product = "FUNCTION_RETAIN_OPTIONAL"
        next_action = "HARDEN_V6_CORE_PRODUCT_WITHOUT_REQUIRED_FUNCTION"
        alternative = "B_MAKE_FUNCTION_OPTIONAL_BEST_EFFORT"
        rationale = (
            "text_only_ceiling_insufficient_for_required_axis;"
            "concepts_retained_as_advisory_best_effort;"
            "core_product_is_gate_domain_mediation"
        )

    revised_contract = revised_v6_output_contract(product)
    release_gate_effects = release_gate_effects_for(product, core_system=core_system)

    return {
        "PRODUCT_DISPOSITION": product,
        "NEXT_ACTION": next_action,
        "selected_contract_alternative": alternative,
        "rationale": rationale,
        "disposition_counts": {
            "KEEP_REQUIRED": n_required,
            "KEEP_OPTIONAL": n_optional,
            "KEEP_RESEARCH_ONLY": n_research,
            "DEPRECATE_FROM_PRODUCT": n_deprecate,
        },
        "revised_v6_output_contract": revised_contract,
        "release_gate_effects": release_gate_effects,
        "core_viable": none_ok and core_system >= 0.30,
        "none_preserved": none_ok,
    }


def revised_v6_output_contract(product_disposition: str) -> dict[str, Any]:
    """Canonical V6 outputs after the product decision."""
    required = ["evidence_gate", "domain", "mediation"]
    optional: list[str] = []
    research: list[str] = []
    excluded: list[str] = []

    if product_disposition == "FUNCTION_RETAIN_REQUIRED":
        required.append("function")
    elif product_disposition == "FUNCTION_RETAIN_OPTIONAL":
        optional.append("function_best_effort")
        research.append("function_contextual_enrichment_track")
    elif product_disposition == "FUNCTION_MOVE_TO_CONTEXTUAL_LAYER":
        research.append("function_contextual_reasoning_subsystem")
        excluded.append("function_from_text_only_classifier")
    else:  # DEPRECATE
        research.append("function_as_research_metadata_only")
        excluded.append("function_from_v6_product_outputs")

    return {
        "required_outputs": required,
        "optional_outputs": optional,
        "research_tracks": research,
        "excluded_from_core": excluded,
        "system_macro_axes": (
            ["domain", "function", "mediation"]
            if product_disposition == "FUNCTION_RETAIN_REQUIRED"
            else ["domain", "mediation"]
        ),
        "FUNCTION_blocks_release": product_disposition == "FUNCTION_RETAIN_REQUIRED",
        "FUNCTION_in_qualification_system_macro": (
            product_disposition == "FUNCTION_RETAIN_REQUIRED"
        ),
        "ontology_labels_preserved": True,
        "note": (
            "Ontology keeps the four function labels for annotation/research; "
            "product requiredness is what changes."
        ),
    }


def release_gate_effects_for(
    product_disposition: str, *, core_system: float
) -> dict[str, Any]:
    """How release/QUAL gates change when FUNCTION is not required."""
    base_gates = dict(OPERATING_QUALIFICATION_GATES)
    if product_disposition == "FUNCTION_RETAIN_REQUIRED":
        return {
            "system_macro_includes_FUNCTION": True,
            "min_axis_macro_applies_to_FUNCTION": True,
            "gates": base_gates,
            "observed_core_system_macro_f1": core_system,
        }
    gates = dict(base_gates)
    gates["system_macro_axes"] = ["domain", "mediation"]
    gates["FUNCTION_axis_gate"] = "not_required"
    gates["FUNCTION_reporting"] = (
        "advisory_only"
        if product_disposition == "FUNCTION_RETAIN_OPTIONAL"
        else "research_or_excluded"
    )
    gates["retention_rule"] = (
        "QUAL core_system_macro_f1(DOMAIN,MEDIATION) >= 0.30; "
        "FUNCTION does not block release"
    )
    return {
        "system_macro_includes_FUNCTION": False,
        "min_axis_macro_applies_to_FUNCTION": False,
        "gates": gates,
        "observed_core_system_macro_f1": core_system,
        "core_meets_legacy_system_floor_0_30": core_system >= 0.30,
    }


def product_requirement_contract() -> dict[str, Any]:
    return {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "parent": dict(PARENT),
        "surfaces": {
            "TRAIN": TRAIN_V3_ID,
            "DEV_SELECTION": DEV_V3_ID,
            "REPRESENTATIVE_VALIDATION": REP_V3_ID,
        },
        "frozen": {
            "encoder_model_id": SELECTED_ENCODER_MODEL_ID,
            "encoder_revision": SELECTED_ENCODER_REVISION,
            "ANY_LABEL_threshold": WITNESS_GATE_THRESHOLD,
            "ontology_changed": False,
            "DOMAIN_head_mutated": False,
            "MEDIATION_head_mutated": False,
            "NONE_gate_mutated": False,
            "operating_package_sha256": EXPECTED_PACKAGE_SHA256,
        },
        "function_vocab": list(FUNCTION_VOCAB),
        "axis_dispositions": list(AXIS_DISPOSITIONS),
        "placement_options": list(PLACEMENT_OPTIONS),
        "product_dispositions": list(PRODUCT_DISPOSITIONS),
        "contract_alternatives": list(CONTRACT_ALTERNATIVES),
        "next_actions": list(NEXT_ACTIONS),
        "forbidden": [
            "train_another_function_model",
            "change_encoder",
            "change_NONE_gate",
            "retrain_DOMAIN",
            "retrain_MEDIATION",
            "change_ontology",
            "rescore_QUAL",
        ],
        "historical_qual": {
            "QUALIFICATION_ID": QUALIFICATION_ID,
            "seal_sha256": EXPECTED_SEAL_SHA256,
            "result_sha256": EXPECTED_QUAL_RESULT_SHA256,
            "role": "BLOCKED_SPENT_SURFACE_READ_ONLY",
        },
        "QUALIFICATION_USED_FOR_OPTIMIZATION": False,
        "QUALIFICATION_RESCORED": False,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "RELEASE_ELIGIBLE": False,
        "rejected_micro_fixes_default": dict(REJECTED_MICRO_FIXES),
        "per_function_evidence_seed": {
            k: {
                "signal_class": v["signal_class"],
                "old_head_f1": v["old_head_f1"],
                "rep_support": v["rep_support"],
            }
            for k, v in PER_FUNCTION_EVIDENCE.items()
        },
    }


def build_product_requirement_receipt(
    audit: Mapping[str, Any], *, sealed_at: str
) -> dict[str, Any]:
    decision = classify_product_disposition(audit)
    body = {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "PRODUCT_DISPOSITION": decision["PRODUCT_DISPOSITION"],
        "NEXT_ACTION": decision["NEXT_ACTION"],
        "selected_contract_alternative": decision["selected_contract_alternative"],
        "rationale": decision["rationale"],
        "revised_v6_output_contract": decision["revised_v6_output_contract"],
        "release_gate_effects": decision["release_gate_effects"],
        "per_function_dispositions": dict(audit.get("per_function_dispositions") or {}),
        "core_without_function": dict(audit.get("core_without_function") or {}),
        "preserved_research_findings": list(
            audit.get("preserved_research_findings") or []
        ),
        "REJECTED_MICRO_FIXES": dict(REJECTED_MICRO_FIXES),
        "QUALIFICATION_USED_FOR_OPTIMIZATION": False,
        "QUALIFICATION_RESCORED": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "RELEASE_ELIGIBLE": False,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "DOMAIN_HEAD_MUTATED": False,
        "MEDIATION_HEAD_MUTATED": False,
        "NONE_GATE_MUTATED": False,
        "ENCODER_MUTATED": False,
        "ONTOLOGY_MUTATED": False,
        "FUNCTION_MODEL_TRAINED": False,
        "sealed_at": sealed_at,
    }
    body["SYSTEM_FUNCTION_PRODUCT_REQUIREMENT_RECEIPT_SHA256"] = _hash(
        {
            k: v
            for k, v in body.items()
            if k != "SYSTEM_FUNCTION_PRODUCT_REQUIREMENT_RECEIPT_SHA256"
        }
    )
    return body


__all__ = [
    "AXIS_DISPOSITIONS",
    "BASELINE_REP_V3",
    "CONTRACT_ALTERNATIVES",
    "EXPERIMENT_ID",
    "FUNCTION_VOCAB",
    "NEXT_ACTIONS",
    "PARENT",
    "PER_FUNCTION_EVIDENCE",
    "PHASE_RULE",
    "PLACEMENT_OPTIONS",
    "PRODUCT_DISPOSITIONS",
    "REJECTED_MICRO_FIXES",
    "build_product_requirement_receipt",
    "classify_product_disposition",
    "core_without_function_metrics",
    "product_requirement_contract",
    "recommend_function_disposition",
    "release_gate_effects_for",
    "revised_v6_output_contract",
]
