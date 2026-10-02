"""REDESIGN_V6_FUNCTION_OBJECTIVE_AROUND_PRAGMATIC_SIGNAL — contracts.

Decompose FUNCTION into text-observable pragmatic primitives; derive legacy
function outputs from primitives where possible. Encoder / NONE / DOMAIN /
MEDIATION / ontology / QUAL remain frozen.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
from .classification_v6_function_diversity_expand import (
    DEV_V3_ID,
    REP_V3_ID,
    TRAIN_V3_ID,
)
from .classification_v6_function_prediction_redesign import BASELINE_REP_V3
from .classification_v6_function_task_signal_reassess import (
    EXPERIMENT_ID as PARENT_SIGNAL_EXPERIMENT,
)
from .classification_v6_human_ontology_settlement import FUNCTION_CUES
from .classification_v6_label_migration import FUNCTION_VOCAB
from .classification_v6_operating_pipeline_harden import WITNESS_GATE_THRESHOLD
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

PHASE_RULE = "REDESIGN_V6_FUNCTION_OBJECTIVE_AROUND_PRAGMATIC_SIGNAL"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-PRAGMATIC-FUNCTION-OBJECTIVE-001"
SCHEMA = "hyperlex.classification.v6.pragmatic_function_objective.v1"

PARENT_DIAGNOSIS = "FUNCTION_TASK_SIGNAL_PARTIAL"
PARENT_CEILING = "TEXT_SIGNAL_CEILING"
PARENT_AXIS = "latent_pragmatic_attributes"

OUTCOMES = (
    "V6_PRAGMATIC_OBJECTIVE_ADVANCE",
    "V6_PRAGMATIC_OBJECTIVE_PARTIAL",
    "V6_PRAGMATIC_OBJECTIVE_NOT_SUPPORTED",
)

NEXT_ACTIONS = (
    "HARDEN_V6_PRAGMATIC_FUNCTION_PIPELINE",
    "COMPLETE_V6_PRAGMATIC_PRIMITIVE_SETTLEMENT",
    "REASSESS_V6_FUNCTION_PRODUCT_REQUIREMENT",
)

OBJECTIVES = (
    "A_PRIMITIVE_MULTILABEL",
    "B_PRIMITIVE_PLUS_DERIVATION",
    "C_PRIMITIVE_PLUS_ABSTENTION",
)

ANNOTATION_STATUSES = (
    "DIRECTLY_DERIVED",
    "RULE_DERIVABLE",
    "HUMAN_RESETTLEMENT_REQUIRED",
    "NOT_IDENTIFIABLE",
)

FUNCTION_MODES = (
    "DIRECT_PREDICTION",
    "DERIVED_PREDICTION",
    "PARTIALLY_DERIVED",
    "UNRESOLVED_WHEN_CONTEXT_MISSING",
)

# Smallest text-observable primitive set derived from settled FUNCTION cues
# and boundary definitions (not an ontology rename).
PRIMITIVE_VOCAB = (
    "prag.normative_judgment",
    "prag.intimate_partnership",
    "prag.hostile_force",
    "prag.memetic_template",
    "prag.mockery_framing",
)

PRIMITIVE_DEFINITIONS = {
    "prag.normative_judgment": (
        "Text marks praise, insult, pejoration, prestige, approval, or "
        "disapproval. Narrower than evaluative_stance: requires observable "
        "judgment language, not inferred social status alone."
    ),
    "prag.intimate_partnership": (
        "Text marks romantic, dating, sexual, or intimate partnership. "
        "Narrower than relational_intimacy: excludes platonic affiliation "
        "and workplace 'partner' without intimacy evidence."
    ),
    "prag.hostile_force": (
        "Text marks hostility, violence, combat, or aggression framing. "
        "Narrower than conflictive_force: excludes metaphorical competition "
        "without hostility sense."
    ),
    "prag.memetic_template": (
        "Text marks meme format, copypasta, image macro, or viral template. "
        "Narrower than memetic_form: viral topic alone is insufficient."
    ),
    "prag.mockery_framing": (
        "Text marks ridicule, satire, parody, or joke-about framing. "
        "Supports memetic/evaluative derivation but is not alone enough for "
        "memetic_form without template evidence."
    ),
}

PRIMITIVE_CUES: dict[str, tuple[str, ...]] = {
    "prag.normative_judgment": tuple(FUNCTION_CUES["evaluative_stance"])
    + ("prestigious", "stigmatiz", "disparag", "laudatory", "belittl"),
    "prag.intimate_partnership": tuple(FUNCTION_CUES["relational_intimacy"])
    + ("lover", "hookup", "flirt", "erotica"),
    "prag.hostile_force": tuple(FUNCTION_CUES["conflictive_force"])
    + ("hostile", "assault", "attack", "brutality", "threaten"),
    "prag.memetic_template": tuple(FUNCTION_CUES["memetic_form"])
    + ("template", "snowclone", "reaction image", "catchphrase format"),
    "prag.mockery_framing": (
        "mock",
        "mockery",
        "ridicule",
        "satire",
        "parody",
        "lampoon",
        "roast",
        "joke about",
        "sarcasm",
        "ironic",
    ),
}

# Legacy function ← primitives mapping (product semantics preserved).
FUNCTION_PRIMITIVE_MAP: dict[str, dict[str, Any]] = {
    "function.evaluative_stance": {
        "expression": "one_primitive",
        "mode": "DERIVED_PREDICTION",
        "require_any": ["prag.normative_judgment"],
        "supportive": ["prag.mockery_framing"],
        "unresolved_if_only": ["prag.mockery_framing"],
    },
    "function.relational_intimacy": {
        "expression": "one_primitive",
        "mode": "DERIVED_PREDICTION",
        "require_any": ["prag.intimate_partnership"],
        "supportive": [],
        "unresolved_if_only": [],
    },
    "function.conflictive_force": {
        "expression": "one_primitive",
        "mode": "DERIVED_PREDICTION",
        "require_any": ["prag.hostile_force"],
        "supportive": [],
        "unresolved_if_only": [],
    },
    "function.memetic_form": {
        "expression": "primitive_plus_contextual_uncertainty",
        "mode": "UNRESOLVED_WHEN_CONTEXT_MISSING",
        "require_any": ["prag.memetic_template"],
        "supportive": ["prag.mockery_framing"],
        "unresolved_if_only": ["prag.mockery_framing"],
    },
}

# Gold function → primary primitive for RULE_DERIVABLE soft projection.
FUNCTION_TO_PRIMARY_PRIMITIVE = {
    "function.evaluative_stance": "prag.normative_judgment",
    "function.relational_intimacy": "prag.intimate_partnership",
    "function.conflictive_force": "prag.hostile_force",
    "function.memetic_form": "prag.memetic_template",
}

IDENTIFIABILITY_LIFT_MIN = 0.15  # primitive cue recovery − function cue recovery
FUNCTION_RELIABILITY_DELTA = 0.02  # material reliability / F1 lift
NONE_ZERO_FP_MAX = 0.35
NONE_ZERO_EXACT_MIN = 0.50

REJECTED_MICRO_FIXES = {
    "change_encoder": False,
    "change_NONE_gate": False,
    "retrain_DOMAIN": False,
    "retrain_MEDIATION": False,
    "change_ontology": False,
    "tune_on_QUAL": False,
    "another_direct_function_head": False,
    "acquire_more_data_by_default": False,
}


def _hash(payload: Any) -> str:
    return sha256_text(canonical_json(payload))


def pragmatic_contract() -> dict[str, Any]:
    return {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "parent": {
            "phase": "REASSESS_V6_FUNCTION_TASK_SIGNAL",
            "experiment": PARENT_SIGNAL_EXPERIMENT,
            "PRIMARY_DIAGNOSIS": PARENT_DIAGNOSIS,
            "CEILING_CLASS": PARENT_CEILING,
            "AXIS_STRUCTURE": PARENT_AXIS,
            "baseline_FUNCTION": BASELINE_REP_V3["FUNCTION_macro_f1"],
        },
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
            "operating_package_sha256": EXPECTED_PACKAGE_SHA256,
        },
        "primitive_vocab": list(PRIMITIVE_VOCAB),
        "primitive_definitions": dict(PRIMITIVE_DEFINITIONS),
        "primitive_cues": {k: list(v) for k, v in PRIMITIVE_CUES.items()},
        "function_vocab": list(FUNCTION_VOCAB),
        "function_primitive_map": dict(FUNCTION_PRIMITIVE_MAP),
        "function_to_primary_primitive": dict(FUNCTION_TO_PRIMARY_PRIMITIVE),
        "objectives": list(OBJECTIVES),
        "annotation_statuses": list(ANNOTATION_STATUSES),
        "function_modes": list(FUNCTION_MODES),
        "outcomes": list(OUTCOMES),
        "next_actions": list(NEXT_ACTIONS),
        "forbidden": [
            "change_encoder",
            "change_NONE_gate",
            "retrain_DOMAIN",
            "retrain_MEDIATION",
            "change_ontology",
            "tune_on_QUAL",
            "another_direct_function_head",
            "acquire_more_data_by_default",
        ],
        "historical_qual": {
            "QUALIFICATION_ID": QUALIFICATION_ID,
            "seal_sha256": EXPECTED_SEAL_SHA256,
            "result_sha256": EXPECTED_QUAL_RESULT_SHA256,
            "role": "BLOCKED_SPENT_SURFACE",
        },
        "QUALIFICATION_USED_FOR_OPTIMIZATION": False,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "RELEASE_ELIGIBLE": False,
        "rejected_micro_fixes_default": dict(REJECTED_MICRO_FIXES),
    }


def detect_primitive_cues(text: str) -> dict[str, list[str]]:
    """Return primitive → cue hits for text (deterministic, metadata-free)."""
    from .classification_v6_human_ontology_settlement import _has_cues

    out: dict[str, list[str]] = {}
    for prim, cues in PRIMITIVE_CUES.items():
        hits = _has_cues(text, cues)
        if hits:
            out[prim] = hits
    return out


def derive_functions_from_primitives(
    primitives: Sequence[str],
    *,
    abstain: bool = False,
) -> dict[str, Any]:
    """Map primitive set → legacy function predictions (+ unresolved flags)."""
    present = set(primitives)
    functions: list[str] = []
    unresolved: list[str] = []
    for fun, spec in FUNCTION_PRIMITIVE_MAP.items():
        req = set(spec["require_any"])
        only = set(spec.get("unresolved_if_only") or [])
        if present & req:
            functions.append(fun)
        elif abstain and (present & only) and not (present & req):
            unresolved.append(fun)
        elif abstain and not (present & req) and not (present & only):
            # no evidence → unresolved rather than forced negative when abstain
            # only mark unresolved if row has some other pragmatic evidence
            # (handled by caller for global FUNCTION_UNRESOLVED)
            pass
    return {
        "function_labels": functions,
        "unresolved_functions": unresolved,
        "FUNCTION_UNRESOLVED": bool(unresolved)
        or (abstain and not functions and bool(present & set(PRIMITIVE_VOCAB))),
    }


def classify_row_annotation_status(
    text: str,
    gold_functions: Sequence[str],
) -> dict[str, Any]:
    """Audit one row under the primitive schema."""
    from .classification_v6_human_ontology_settlement import _is_markup_noise

    gold = [g for g in gold_functions if g in FUNCTION_VOCAB]
    if _is_markup_noise(text) or len((text or "").strip()) < 8:
        return {
            "status": "NOT_IDENTIFIABLE",
            "cue_primitives": [],
            "rule_primitives": [],
            "missing_for_gold": list(gold),
        }

    cues = detect_primitive_cues(text)
    cue_prims = sorted(cues)
    rule_prims = sorted(
        {
            FUNCTION_TO_PRIMARY_PRIMITIVE[g]
            for g in gold
            if g in FUNCTION_TO_PRIMARY_PRIMITIVE
        }
    )
    missing = [
        g
        for g in gold
        if FUNCTION_TO_PRIMARY_PRIMITIVE.get(g) not in cues
    ]

    if gold and not missing:
        # every gold function has its primary primitive cue in text
        status = "DIRECTLY_DERIVED"
    elif gold and missing:
        # gold function not recoverable from text cues → needs human settlement
        # (rule projection exists but is not text-grounded)
        status = "HUMAN_RESETTLEMENT_REQUIRED"
    else:
        # no gold functions: cue positives and clear negatives are both derived
        status = "DIRECTLY_DERIVED"

    return {
        "status": status,
        "cue_primitives": cue_prims,
        "rule_primitives": rule_prims,
        "missing_for_gold": missing,
        "cue_hits": cues,
    }


def function_mode_summary() -> dict[str, str]:
    return {fun: str(spec["mode"]) for fun, spec in FUNCTION_PRIMITIVE_MAP.items()}


def classify_pragmatic_outcome(audit: Mapping[str, Any]) -> dict[str, Any]:
    """Decide ADVANCE / PARTIAL / NOT_SUPPORTED + NEXT_ACTION."""
    ident_lift = float(audit.get("identifiability_lift") or 0.0)
    prim_agree = float(audit.get("primitive_dual_agreement") or 0.0)
    fun_agree = float(audit.get("function_dual_agreement") or 0.0)
    agree_lift = prim_agree - fun_agree
    resettlement_share = float(audit.get("human_resettlement_share") or 0.0)
    cue_pos_rep = int(
        (audit.get("cue_positive_rows") or {}).get("REP")
        or audit.get("cue_positive_rep")
        or 0
    )
    # Primitives are more reproducible when dual-protocol agreement is high and
    # either (a) they beat function agreement/recovery, or (b) old function gold
    # is largely non-text-identifiable while primitives remain self-consistent.
    primitives_more_reproducible = prim_agree >= 0.80 and (
        ident_lift >= IDENTIFIABILITY_LIFT_MIN
        or agree_lift >= 0.10
        or (
            resettlement_share >= 0.35
            and cue_pos_rep >= 15
            and prim_agree >= fun_agree
        )
    )

    none_ok = bool(audit.get("none_preserved", False))
    derived_f1 = float(audit.get("derived_FUNCTION_macro_f1") or 0.0)
    baseline_f1 = float(
        audit.get("baseline_FUNCTION_macro_f1")
        or BASELINE_REP_V3["FUNCTION_macro_f1"]
    )
    false_emission = float(audit.get("false_function_emission") or 1.0)
    baseline_false = float(audit.get("baseline_false_function_emission") or 1.0)
    resolved_precision = audit.get("resolved_function_precision")
    unresolved_rate = float(audit.get("unresolved_rate") or 0.0)

    reliability_better = (
        derived_f1 >= baseline_f1 + FUNCTION_RELIABILITY_DELTA
        or (
            false_emission <= baseline_false - 0.05
            and derived_f1 >= baseline_f1 - 0.03
        )
        or (
            resolved_precision is not None
            and float(resolved_precision) >= 0.45
            and unresolved_rate >= 0.20
            and derived_f1 >= baseline_f1 - 0.05
        )
    )

    selected = audit.get("selected_objective")

    if not primitives_more_reproducible:
        return {
            "OUTCOME": "V6_PRAGMATIC_OBJECTIVE_NOT_SUPPORTED",
            "NEXT_ACTION": "REASSESS_V6_FUNCTION_PRODUCT_REQUIREMENT",
            "selected_objective": None,
            "primitives_more_reproducible": False,
            "reliability_better": reliability_better,
            "none_preserved": none_ok,
            "reason": "primitives_not_more_reproducible_from_text",
        }

    if (
        primitives_more_reproducible
        and reliability_better
        and none_ok
        and selected
        and resettlement_share < 0.55
    ):
        return {
            "OUTCOME": "V6_PRAGMATIC_OBJECTIVE_ADVANCE",
            "NEXT_ACTION": "HARDEN_V6_PRAGMATIC_FUNCTION_PIPELINE",
            "selected_objective": selected,
            "primitives_more_reproducible": True,
            "reliability_better": True,
            "none_preserved": none_ok,
            "reason": "identifiability_and_reliability_improved",
        }

    if primitives_more_reproducible and resettlement_share >= 0.35:
        return {
            "OUTCOME": "V6_PRAGMATIC_OBJECTIVE_PARTIAL",
            "NEXT_ACTION": "COMPLETE_V6_PRAGMATIC_PRIMITIVE_SETTLEMENT",
            "selected_objective": selected,
            "primitives_more_reproducible": True,
            "reliability_better": reliability_better,
            "none_preserved": none_ok,
            "reason": "primitives_stable_need_human_settlement",
        }

    if primitives_more_reproducible and none_ok:
        return {
            "OUTCOME": "V6_PRAGMATIC_OBJECTIVE_PARTIAL",
            "NEXT_ACTION": "COMPLETE_V6_PRAGMATIC_PRIMITIVE_SETTLEMENT",
            "selected_objective": selected,
            "primitives_more_reproducible": True,
            "reliability_better": reliability_better,
            "none_preserved": none_ok,
            "reason": "partial_identifiability_without_full_reliability_gain",
        }

    return {
        "OUTCOME": "V6_PRAGMATIC_OBJECTIVE_NOT_SUPPORTED",
        "NEXT_ACTION": "REASSESS_V6_FUNCTION_PRODUCT_REQUIREMENT",
        "selected_objective": None,
        "primitives_more_reproducible": primitives_more_reproducible,
        "reliability_better": reliability_better,
        "none_preserved": none_ok,
        "reason": "decomposition_did_not_improve_learnability",
    }


def build_pragmatic_receipt(
    audit: Mapping[str, Any], *, sealed_at: str
) -> dict[str, Any]:
    decision = classify_pragmatic_outcome(audit)
    body = {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "OUTCOME": decision["OUTCOME"],
        "NEXT_ACTION": decision["NEXT_ACTION"],
        "selected_objective": decision["selected_objective"],
        "primitives_more_reproducible": decision["primitives_more_reproducible"],
        "reliability_better": decision["reliability_better"],
        "function_modes": function_mode_summary(),
        "primitive_vocab": list(PRIMITIVE_VOCAB),
        "audit": dict(audit),
        "REJECTED_MICRO_FIXES": dict(REJECTED_MICRO_FIXES),
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
        "DIRECT_FUNCTION_HEAD_ADDED": False,
        "sealed_at": sealed_at,
    }
    body["SYSTEM_PRAGMATIC_OBJECTIVE_RECEIPT_SHA256"] = _hash(
        {
            k: v
            for k, v in body.items()
            if k != "SYSTEM_PRAGMATIC_OBJECTIVE_RECEIPT_SHA256"
        }
    )
    return body


__all__ = [
    "ANNOTATION_STATUSES",
    "EXPERIMENT_ID",
    "FUNCTION_PRIMITIVE_MAP",
    "FUNCTION_TO_PRIMARY_PRIMITIVE",
    "FUNCTION_VOCAB",
    "NEXT_ACTIONS",
    "OBJECTIVES",
    "OUTCOMES",
    "PHASE_RULE",
    "PRIMITIVE_CUES",
    "PRIMITIVE_DEFINITIONS",
    "PRIMITIVE_VOCAB",
    "REJECTED_MICRO_FIXES",
    "build_pragmatic_receipt",
    "classify_pragmatic_outcome",
    "classify_row_annotation_status",
    "derive_functions_from_primitives",
    "detect_primitive_cues",
    "function_mode_summary",
    "pragmatic_contract",
]
