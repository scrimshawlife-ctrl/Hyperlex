"""REBASE_V6_ON_STRONGER_PRETRAINED_SEMANTIC_ENCODER — contracts.

Semantic-embedding rebase. No A–F carousel. Floors locked. QUAL sealed.
MODEL_WIDE_BEST is historical control only and is not mutated.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
from .classification_v6_architecture_bakeoff import GENERALIZATION_GAP_GATE
from .classification_v6_architecture_reset_bakeoff import LABEL_DESCRIPTIONS
from .classification_v6_label_migration import (
    DOMAIN_VOCAB,
    FUNCTION_VOCAB,
    MEDIATION_VOCAB,
)
from .classification_v6_task_signal_reassessment import oracle_description

PHASE_RULE = "REBASE_V6_ON_STRONGER_PRETRAINED_SEMANTIC_ENCODER"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-REPRESENTATION-REBASE-001"
SCHEMA = "hyperlex.classification.v6.representation_rebase.v1"

MPNET_WITNESS = {
    "id": "ENCODER_CANDIDATE_1",
    "model_id": "sentence-transformers/all-mpnet-base-v2",
    "ZERO_SHOT_REP_SYSTEM_MACRO_F1": 0.20555757451039375,
    "source_receipt": "8703b73df6aca08ed5cfa6b847fe753997af537b4d15bcf0650a14113d5e2549",
    "role": "REPRESENTATION_REBASE_BASELINE",
}

MODERNBERT_CONTROL = {
    "role": "HISTORICAL_CONTROL_REPRESENTATION",
    "sha256": MODEL_WIDE_BEST_SHA256,
    "zero_shot_rep_system_macro_f1": 0.1622371780444463,
    "do_not_initialize_from": True,
    "do_not_mutate": True,
}

ENCODER_FAMILY = {
    "A_MPNET": "sentence-transformers/all-mpnet-base-v2",
    "B_BGE_BASE": "BAAI/bge-base-en-v1.5",
    "C_MSMARCO": "sentence-transformers/msmarco-distilbert-base-v4",
}

REBASE_STATES = (
    "V6_REPRESENTATION_REBASE_ADVANCE",
    "V6_REPRESENTATION_REBASE_ZERO_SHOT_ONLY",
    "V6_REPRESENTATION_REBASE_NO_ADVANCE",
)

ADVANCEMENT = {
    "min_rep_system_macro_f1": 0.20,
    "max_hierarchy_violation_rate_rep": 0.05,
    "min_axis_macro_f1": 0.10,
    "mpnet_witness": MPNET_WITNESS["ZERO_SHOT_REP_SYSTEM_MACRO_F1"],
    "trained_improvement_bar": MPNET_WITNESS["ZERO_SHOT_REP_SYSTEM_MACRO_F1"],
    "trained_tolerance": 0.005,
    "max_macro_f1_dev_minus_rep": float(
        GENERALIZATION_GAP_GATE["max_macro_f1_dev_minus_rep"]
    ),
    "floors_locked": True,
}

LABEL_STRENGTH = {
    "DEAD_LABEL": 0.05,
    "WEAK_LABEL": 0.15,
    "STABLE_LABEL": 0.35,
    "min_support_for_strength": 8,
}


def rebase_contract() -> dict[str, Any]:
    return {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "mpnet_witness": MPNET_WITNESS,
        "historical_control": MODERNBERT_CONTROL,
        "encoder_family": ENCODER_FAMILY,
        "advancement": ADVANCEMENT,
        "forbidden": [
            "reopen_ontology",
            "inspect_QUAL",
            "lower_advancement_floors",
            "unconstrained_architecture_bakeoff",
            "mutate_V5",
            "mutate_MODEL_WIDE_BEST",
            "full_finetune_unless_peft_justifies",
            "tune_on_REP",
            "expand_TRAIN",
        ],
        "formulations": [
            "direct_text_label_similarity",
            "learned_calibration_on_similarity",
            "frozen_embedding_linear_heads",
            "frozen_embedding_nonlinear_heads",
            "axis_specific_projections",
            "parameter_efficient_adapter",
        ],
        "label_text_variants": ["short_definition", "full_boundary_contract"],
        "qual_policy": {
            "HYPERLEX_V6_QUALIFICATION_001": "REMAIN_SEALED",
            "inspected": False,
        },
        "pointer_policy": {
            "MODEL_WIDE_BEST": "UNCHANGED",
            "STAGE_A_BEST": "UNCHANGED",
            "V6_REPRESENTATION_CANDIDATE": "created_only_on_advance",
        },
    }


def label_texts(variant: str) -> dict[str, str]:
    if variant == "short_definition":
        return dict(LABEL_DESCRIPTIONS)
    if variant == "full_boundary_contract":
        return {lab: oracle_description(lab) for lab in LABEL_DESCRIPTIONS}
    raise ValueError(variant)


def classify_label_strength(f1: float, support: int) -> str:
    if support < LABEL_STRENGTH["min_support_for_strength"]:
        return "LOW_SUPPORT"
    if f1 < LABEL_STRENGTH["DEAD_LABEL"]:
        return "DEAD_LABEL"
    if f1 < LABEL_STRENGTH["WEAK_LABEL"]:
        return "WEAK_LABEL"
    if f1 < LABEL_STRENGTH["STABLE_LABEL"]:
        return "STABLE_LABEL"
    return "STRONG_LABEL"


def axis_collapse(rep_axes: Mapping[str, Mapping[str, Any]]) -> bool:
    floor = ADVANCEMENT["min_axis_macro_f1"]
    for axis in ("domain", "function", "mediation"):
        macro = float((rep_axes.get(axis) or {}).get("macro_f1") or 0.0)
        if macro < floor:
            return True
    return False


def classify_geometry(
    *,
    cosine_drift: float,
    nn_retention: float,
    margin_delta: float,
    rep_delta: float,
) -> str:
    """Relative to pretrained MPNet embeddings."""
    if cosine_drift < 0.90 or nn_retention < 0.70 or (margin_delta < -0.02 and rep_delta < 0):
        return "SEMANTIC_GEOMETRY_DEGRADED"
    if rep_delta > 0.01 and margin_delta >= -0.005:
        return "SEMANTIC_GEOMETRY_MODIFIED_PRODUCTIVELY"
    return "SEMANTIC_GEOMETRY_PRESERVED"


def eligible_candidate(row: Mapping[str, Any]) -> bool:
    def _f(key: str, default: float) -> float:
        val = row.get(key)
        if val is None:
            return default
        return float(val)

    rep = _f("rep_system_macro_f1", 0.0)
    viol = _f("hierarchy_violation_rate_rep", 1.0)
    gap = _f("dev_macro_f1", 0.0) - rep
    if rep < ADVANCEMENT["min_rep_system_macro_f1"]:
        return False
    if viol > ADVANCEMENT["max_hierarchy_violation_rate_rep"]:
        return False
    if gap > ADVANCEMENT["max_macro_f1_dev_minus_rep"]:
        return False
    if row.get("axis_collapse"):
        return False
    if row.get("geometry") == "SEMANTIC_GEOMETRY_DEGRADED":
        return False
    return True


def select_rebase_state(candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Choose ADVANCE / ZERO_SHOT_ONLY / NO_ADVANCE and next action."""
    witness = ADVANCEMENT["mpnet_witness"]
    valid = [c for c in candidates if eligible_candidate(c)]
    valid.sort(key=lambda c: float(c.get("rep_system_macro_f1") or 0.0), reverse=True)
    trained_valid = [
        c
        for c in valid
        if not str(c.get("formulation") or "").startswith("zero_shot")
    ]
    zs_valid = [c for c in valid if str(c.get("formulation") or "").startswith("zero_shot")]

    improvement_bar = ADVANCEMENT["trained_improvement_bar"]
    improved = [
        c
        for c in trained_valid
        if float(c.get("rep_system_macro_f1") or 0.0) > improvement_bar
    ]

    if improved:
        winner = improved[0]
        state = "V6_REPRESENTATION_REBASE_ADVANCE"
        next_action = "HARDEN_V6_SEMANTIC_REPRESENTATION_AND_PREPARE_QUALIFICATION"
        selected = winner.get("id")
    elif zs_valid:
        winner = zs_valid[0]
        state = "V6_REPRESENTATION_REBASE_ZERO_SHOT_ONLY"
        next_action = "HARDEN_V6_ZERO_SHOT_SEMANTIC_MATCHING_PIPELINE"
        selected = winner.get("id")
    elif valid:
        # trained cleared 0.20 but not witness — still valid minimum advance,
        # but zero-shot remains preferred if present among all candidates
        winner = valid[0]
        if str(winner.get("formulation") or "").startswith("zero_shot"):
            state = "V6_REPRESENTATION_REBASE_ZERO_SHOT_ONLY"
            next_action = "HARDEN_V6_ZERO_SHOT_SEMANTIC_MATCHING_PIPELINE"
        else:
            # minimum advance without beating witness
            state = "V6_REPRESENTATION_REBASE_ZERO_SHOT_ONLY"
            next_action = "HARDEN_V6_ZERO_SHOT_SEMANTIC_MATCHING_PIPELINE"
        selected = winner.get("id")
    else:
        winner = None
        state = "V6_REPRESENTATION_REBASE_NO_ADVANCE"
        next_action = "REASSESS_V6_SIGNAL_REQUIREMENTS_OR_DATA_SCALE"
        selected = None

    return {
        "REBASE_STATE": state,
        "NEXT_ACTION": next_action,
        "selected": selected,
        "selected_row": winner,
        "valid_ids": [c.get("id") for c in valid],
        "improved_over_witness": [c.get("id") for c in improved],
        "mpnet_witness": witness,
        "MINIMUM_ADVANCE": any(
            float(c.get("rep_system_macro_f1") or 0) >= 0.20 for c in valid
        ),
        "REPRESENTATION_IMPROVEMENT": bool(improved),
    }
