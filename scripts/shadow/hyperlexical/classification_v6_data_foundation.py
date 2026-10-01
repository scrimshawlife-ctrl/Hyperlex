"""BUILD_REPRESENTATIVE_V6_DATA_FOUNDATION — contracts and settlement.

Data/measurement phase only. No V6 train, no V5 retune, no architecture choice.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .classification_v2 import ACTIVE_FAMILY_VOCABULARY
from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
from .classification_v5_stage_a_gold_identifiability_contract import (
    CONTRACT_ID as GOLD_CONTRACT_ID,
    MODEL_INPUT,
)
from .classification_v6_v5_research_baseline import BASELINE_ID

PHASE_RULE = "BUILD_REPRESENTATIVE_V6_DATA_FOUNDATION"
FOUNDATION_ID = "HYPERLEX_V6_DATA_FOUNDATION_V1"
OPERATING_DISTRIBUTION_ID = "HYPERLEX_V6_OPERATING_DISTRIBUTION_V1"
QUALIFICATION_HOLD_ID = "HYPERLEX_V6_QUALIFICATION_001"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-DATA-FOUNDATION-001"
SCHEMA = "hyperlex.classification.v6.data_foundation.v1"

DATASET_ROLES = (
    "TRAIN",
    "DEVELOPMENT_VALIDATION",
    "REPRESENTATIVE_VALIDATION",
    "QUALIFICATION",
)

CONSTRUCTION_TAGS = ("NATURAL", "MATCHED_CONTRAST", "SYNTHETIC", "DERIVED")
ROLE_CLASS = ("PRODUCT_EXPECTED", "RESEARCH_USEFUL", "DIAGNOSTIC_ONLY")
ONTOLOGY_PAIR_CLASSES = (
    "CLEARLY_SEPARABLE",
    "BOUNDARY_SENSITIVE",
    "STRUCTURALLY_OVERLAPPING",
    "ONTOLOGY_REVIEW_REQUIRED",
)

# Acquisition targets (foundation support floors, not training loss weights).
MAX_FAMILY_SHARE_TRAIN = 0.15
REP_VAL_PREFERRED_MIN = 1000
QUAL_PREFERRED_MIN = 400
TRAIN_PREFERRED_MIN = 2000
DEV_VAL_PREFERRED_MIN = 500
OBSERVED_MAJORITY_MIN = 0.50
NATURAL_MAJORITY_REP_QUAL_MIN = 0.80

# Architecture decision gate requirements (section 22).
READY_GATES = (
    "OPERATING_DISTRIBUTION_DEFINED",
    "GOLD_CONTRACT_VALID",
    "ONTOLOGY_AUDITED",
    "TRAIN_READY",
    "DEV_VALIDATION_READY",
    "REPRESENTATIVE_VALIDATION_READY",
    "QUALIFICATION_SEALED",
    "BASE_REPRESENTATION_AUDITED",
)

NEXT_READY = "DESIGN_AND_EXECUTE_HYPERLEX_V6_MODEL_PHASE"
NEXT_ONTOLOGY = "REVISE_HYPERLEX_V6_ONTOLOGY_BEFORE_MODELING"
NEXT_ACQUIRE = "CONTINUE_V6_REPRESENTATIVE_DATA_ACQUISITION"


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def operating_distribution_v1() -> dict[str, Any]:
    """Derive intended production input contract from existing Hyperlex specs."""
    return {
        "OPERATING_DISTRIBUTION_ID": OPERATING_DISTRIBUTION_ID,
        "derived_from": [
            "specs/007-hyperlexical-model/classification-architecture-v3.md",
            "HYPERLEX_STAGE_A_GOLD_IDENTIFIABILITY_CONTRACT_V1",
            "specs/007-hyperlexical-model/classification-v3-evaluation.md",
            "V5 qualification failure system review (negative evidence)",
        ],
        "model_input": list(MODEL_INPUT),
        "gold_identifiability_contract": GOLD_CONTRACT_ID,
        "active_family_vocabulary": list(ACTIVE_FAMILY_VOCABULARY),
        "expected_text_lengths": {
            "short_atom_chars": "<40",
            "medium_chars": "40-160",
            "longer_prose_chars": ">160",
            "product_mix_note": (
                "Operating traffic mixes short slang atoms, dictionary-like glosses, "
                "and conversational/declarative prose; no single band dominates."
            ),
            "role": "PRODUCT_EXPECTED",
        },
        "natural_source_types": {
            "product_expected": [
                "naturally occurring slang/meme/domain mentions",
                "conversational fragments",
                "declarative prose with lexical evidence",
                "dictionary-like definitions when self-contained in text",
            ],
            "research_useful": [
                "wiktionary sense lines with explicit English labels",
                "encyclopedia ordinary-domain negatives",
            ],
            "diagnostic_only": [
                "matched positive/negative contrast pairs",
                "constructed lookalike batteries",
                "synthetic templates",
            ],
        },
        "observed_vs_inferred": {
            "representative_validation_target_observed_min": OBSERVED_MAJORITY_MIN,
            "qualification_target_observed_min": OBSERVED_MAJORITY_MIN,
            "train_may_include_inferred": True,
            "role": "PRODUCT_EXPECTED",
        },
        "short_form_vs_prose": {
            "include_short": True,
            "include_medium": True,
            "include_longer_prose": True,
            "avoid_overfit_to_matched_definition_pairs": True,
            "role": "PRODUCT_EXPECTED",
        },
        "text_registers": {
            "dictionary_like": "RESEARCH_USEFUL",
            "conversational": "PRODUCT_EXPECTED",
            "declarative": "PRODUCT_EXPECTED",
        },
        "expected_domain_mix": {
            "active_family_domains": list(ACTIVE_FAMILY_VOCABULARY),
            "ordinary_no_relation_domains": [
                "mycology",
                "entomology",
                "oceanography",
                "paleontology",
                "cartography",
                "numismatics",
                "philately",
                "archaeology",
                "hydrology",
                "mineralogy",
                "botany",
                "chemistry",
            ],
            "domain_irrelevant": [
                "infrastructure lists",
                "calendar/year pages",
                "generic geographic inventories",
            ],
            "role": "PRODUCT_EXPECTED",
        },
        "expected_family_mix": {
            "bounded_train_max_share": MAX_FAMILY_SHARE_TRAIN,
            "forbid_unjustified_ai_native_index_domination": True,
            "historical_failure_example": "ai-native ≈ 42.6% of V5 Stage-B index",
            "representative_validation_uses_natural_prevalence": True,
            "also_report_macro_family_metrics": True,
            "role": "PRODUCT_EXPECTED",
        },
        "expected_ambiguity": {
            "include_genuine_textual_uncertainty": True,
            "exclude_hidden_metadata_uncertainty": True,
            "role": "PRODUCT_EXPECTED",
        },
        "expected_domain_irrelevant_traffic": {
            "include_when_admissible": True,
            "v5_status": "NOT_ESTABLISHED",
            "role": "PRODUCT_EXPECTED",
        },
        "relation_prevalence": {
            "note": (
                "Operating traffic is majority NO_EVIDENCE / non-entry relative to "
                "active-family evidence; PRESENT is the minority retrieval-trigger class."
            ),
            "representative_validation_should_not_force_50_50": True,
            "role": "PRODUCT_EXPECTED",
        },
        "v5_negative_lessons": {
            "do_not_dominate_with_paired_contrasts": True,
            "do_not_use_inferred_template_buckets_as_operating_proxy": True,
            "do_not_tune_floors_only_on_matched_dev_surface": True,
            "qualification_is_hard_but_valid_not_pathological": True,
        },
        "schema": "hyperlex.classification.v6.operating_distribution.v1",
    }


def dataset_role_contract() -> dict[str, Any]:
    return {
        "roles": list(DATASET_ROLES),
        "TRAIN": {
            "optimizable": True,
            "preferred_min_rows": TRAIN_PREFERRED_MIN,
            "max_family_share": MAX_FAMILY_SHARE_TRAIN,
            "construction": "prefer NATURAL; MATCHED_CONTRAST auxiliary only",
        },
        "DEVELOPMENT_VALIDATION": {
            "optimizable": "checkpoint_selection_and_ordinary_debugging_only",
            "preferred_min_rows": DEV_VAL_PREFERRED_MIN,
            "row_level_repeated_optimization": False,
        },
        "REPRESENTATIVE_VALIDATION": {
            "approximates_operating_conditions": True,
            "preferred_min_rows": REP_VAL_PREFERRED_MIN,
            "observed_min_share": OBSERVED_MAJORITY_MIN,
            "natural_min_share": NATURAL_MAJORITY_REP_QUAL_MIN,
            "row_level_repeated_optimization": False,
            "report_vs_dev_every_eval": True,
        },
        "QUALIFICATION": {
            "id": QUALIFICATION_HOLD_ID,
            "one_shot": True,
            "unavailable_during_model_development": True,
            "expose_during_dev": [
                "manifest_metadata",
                "row_count",
                "coverage_summaries",
                "hashes",
            ],
            "preferred_min_rows": QUAL_PREFERRED_MIN,
            "natural_min_share": NATURAL_MAJORITY_REP_QUAL_MIN,
            "observed_min_share": OBSERVED_MAJORITY_MIN,
        },
        "blocked_lineage_sources": [
            "historical_spent_reserves",
            "HYPERLEX_V5_PIPELINE_QUALIFICATION_001",
            "V1R2_as_v6_operating_proxy",
        ],
    }


def evaluation_contract_v1() -> dict[str, Any]:
    return {
        "stage_a": [
            "false_entry",
            "PRESENT_recall",
            "NONE_recall",
            "UNCERTAIN_recall",
            "macro_F1",
        ],
        "stage_b": [
            "family_precision",
            "macro_family_F1",
            "top1",
            "top2",
            "selective_accuracy",
            "coverage",
        ],
        "system": [
            "end_to_end_family_precision",
            "end_to_end_family_recall",
            "abstention",
            "Stage_A_induced_errors",
            "Stage_B_induced_errors",
            "compound_errors",
        ],
        "distribution_shift_reporting": {
            "always_report_side_by_side": [
                "DEVELOPMENT_VALIDATION",
                "REPRESENTATIVE_VALIDATION",
            ],
            "large_delta_is_first_class_failure_signal": True,
        },
        "preregistered_before_train": True,
    }


def gold_contract_binding() -> dict[str, Any]:
    return {
        "contract": GOLD_CONTRACT_ID,
        "model_input": list(MODEL_INPUT),
        "auto_relabel": False,
        "hidden_fields_cannot_determine_definitive_gold": [
            "domain_metadata",
            "source_metadata",
            "subtype",
            "pair_context",
            "provenance",
            "dictionary_sense",
        ],
        "valid": True,
    }


def classify_ontology_pair(
    *,
    definition_overlap: float,
    embedding_overlap: float,
    lexical_overlap: float,
    boundary_clarity: float,
) -> str:
    """Heuristic pair class for audit (not an auto merge/split)."""
    if embedding_overlap >= 0.90 or definition_overlap >= 0.75:
        return "ONTOLOGY_REVIEW_REQUIRED"
    if embedding_overlap >= 0.85 or lexical_overlap >= 0.40:
        return "STRUCTURALLY_OVERLAPPING"
    if embedding_overlap >= 0.75 or boundary_clarity < 0.5:
        return "BOUNDARY_SENSITIVE"
    return "CLEARLY_SEPARABLE"


def representation_viability(
    *,
    present_none_centroid_cosine: float | None,
    within_family_sim: float | None,
    between_family_sim: float | None,
    nearest_family_purity: float | None,
) -> str:
    if (
        present_none_centroid_cosine is None
        or within_family_sim is None
        or between_family_sim is None
        or nearest_family_purity is None
    ):
        return "BASE_REPRESENTATION_PARTIAL"
    margin = within_family_sim - between_family_sim
    if (
        present_none_centroid_cosine <= 0.85
        and margin >= 0.10
        and nearest_family_purity >= 0.40
    ):
        return "BASE_REPRESENTATION_ADEQUATE"
    if margin < 0.0 or nearest_family_purity < 0.20 or present_none_centroid_cosine >= 0.92:
        return "BASE_REPRESENTATION_INADEQUATE"
    return "BASE_REPRESENTATION_PARTIAL"


def retrieval_viability(
    *,
    family_precision: float | None,
    top1: float | None,
    coverage: float | None,
) -> str:
    if family_precision is None or top1 is None:
        return "RETRIEVAL_PARTIAL"
    if family_precision >= 0.70 and top1 >= 0.55 and (coverage or 0) >= 0.40:
        return "RETRIEVAL_VIABLE"
    if family_precision < 0.35 or top1 < 0.25:
        return "RETRIEVAL_NOT_VIABLE"
    return "RETRIEVAL_PARTIAL"


def foundation_disposition(gates: Mapping[str, bool], *, ontology_structurally_broken: bool) -> dict[str, Any]:
    ready = all(gates.get(g) for g in READY_GATES)
    if ready and ontology_structurally_broken:
        return {
            "V6_DATA_FOUNDATION_STATE": "V6_DATA_FOUNDATION_PARTIAL",
            "NEXT_ACTION": NEXT_ONTOLOGY,
        }
    if ready:
        return {
            "V6_DATA_FOUNDATION_STATE": "V6_DATA_FOUNDATION_READY",
            "NEXT_ACTION": NEXT_READY,
        }
    # Distinguish blocked vs partial: blocked if operating dist or gold contract missing.
    critical = (
        gates.get("OPERATING_DISTRIBUTION_DEFINED")
        and gates.get("GOLD_CONTRACT_VALID")
    )
    if not critical:
        return {
            "V6_DATA_FOUNDATION_STATE": "V6_DATA_FOUNDATION_BLOCKED",
            "NEXT_ACTION": NEXT_ACQUIRE,
        }
    return {
        "V6_DATA_FOUNDATION_STATE": "V6_DATA_FOUNDATION_PARTIAL",
        "NEXT_ACTION": NEXT_ACQUIRE
        if not gates.get("TRAIN_READY")
        or not gates.get("REPRESENTATIVE_VALIDATION_READY")
        else NEXT_ONTOLOGY
        if ontology_structurally_broken
        else NEXT_ACQUIRE,
    }


def build_foundation_receipt(
    *,
    code_revision: str,
    audit: Mapping[str, Any],
    gates: Mapping[str, bool],
    settled_at: str | None = None,
) -> dict[str, Any]:
    ontology_broken = bool(audit.get("ontology_structurally_broken"))
    disp = foundation_disposition(gates, ontology_structurally_broken=ontology_broken)
    payload = {
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "FOUNDATION_ID": FOUNDATION_ID,
        "PHASE_RULE": PHASE_RULE,
        "V5_RESEARCH_BASELINE": BASELINE_ID,
        "OPERATING_DISTRIBUTION_ID": OPERATING_DISTRIBUTION_ID,
        "QUALIFICATION_HOLD_ID": QUALIFICATION_HOLD_ID,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "GOLD_CONTRACT": GOLD_CONTRACT_ID,
        "TRAIN": False,
        "V5_RETUNED": False,
        "V5_CANONICAL_MUTATED": False,
        "ARCHITECTURE_CHOSEN": False,
        "SPENT_QUALIFICATION_USED_FOR_OPTIMIZATION": False,
        "gates": dict(gates),
        "operating_distribution": operating_distribution_v1(),
        "dataset_roles": dataset_role_contract(),
        "evaluation_contract": evaluation_contract_v1(),
        "gold_contract": gold_contract_binding(),
        "audit": dict(audit),
        "code_revision": code_revision,
        "settled_at": settled_at or utc_now_iso(),
        "schema": SCHEMA,
        **disp,
    }
    payload["V6_DATA_FOUNDATION_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in payload.items()
                if k != "V6_DATA_FOUNDATION_RECEIPT_SHA256"
            }
        )
    )
    return payload


def summarize_split_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    from collections import Counter

    n = len(rows)
    if n == 0:
        return {"n": 0}
    labels = Counter(r.get("evidence_label") for r in rows)
    families = Counter(
        r.get("gold_family")
        for r in rows
        if r.get("evidence_label") == "EVIDENCE_PRESENT" and r.get("gold_family")
    )
    observed = sum(1 for r in rows if r.get("provenance") == "OBSERVED" or r.get("class") == "OBSERVED")
    natural = sum(1 for r in rows if r.get("construction_tag") == "NATURAL")
    sources = Counter(r.get("source_family") for r in rows)
    max_fam = max(families.values()) / max(1, sum(families.values())) if families else 0.0
    return {
        "n": n,
        "labels": dict(labels),
        "n_families_present": len(families),
        "family_counts": dict(families),
        "max_family_share_among_present": max_fam,
        "observed_share": observed / n,
        "natural_share": natural / n,
        "construction": dict(Counter(r.get("construction_tag") for r in rows)),
        "provenance": dict(
            Counter(r.get("provenance") or r.get("class") for r in rows)
        ),
        "source_family_top": sources.most_common(12),
        "length": {
            "mean": sum(len(r.get("text") or "") for r in rows) / n,
            "short": sum(1 for r in rows if len(r.get("text") or "") < 40),
            "med": sum(1 for r in rows if 40 <= len(r.get("text") or "") < 160),
            "long": sum(1 for r in rows if len(r.get("text") or "") >= 160),
        },
    }
