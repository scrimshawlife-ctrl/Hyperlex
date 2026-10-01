"""REASSESS_V6_TASK_SIGNAL_AND_PRETRAINED_REPRESENTATION — diagnostic contracts.

No architecture-family bakeoff. Floors locked. QUAL sealed. Ontology frozen.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .classification_v6_architecture_reset_bakeoff import (
    ADVANCEMENT_GATE,
    LABEL_DESCRIPTIONS,
    PRIOR_RECEIPT as RESET_RECEIPT,
    frozen_label_descriptions,
)
from .classification_v6_label_migration import (
    DOMAIN_VOCAB,
    FUNCTION_VOCAB,
    MEDIATION_VOCAB,
)

PHASE_RULE = "REASSESS_V6_TASK_SIGNAL_AND_PRETRAINED_REPRESENTATION"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-TASK-SIGNAL-REASSESSMENT-001"
SCHEMA = "hyperlex.classification.v6.task_signal_reassessment.v1"

# Frozen reference from architecture-reset bakeoff — do not silently replace.
ZERO_SHOT_REFERENCE = {
    "id": "ZERO_SHOT_CONTROL_REP_SYSTEM_MACRO_F1",
    "track": "ZERO_SHOT_SEMANTIC_MATCH__CONTROL",
    "rep_system_macro_f1": 0.1622371780444463,
    "source_receipt": "e7264a0f140dee6536b4ca9d4de69a0ae2139c29a5c3a4572214fa1ae52b58eb",
    "prior_reset_receipt": RESET_RECEIPT,
    "note": "Baseline to beat; description experiments are diagnostic only.",
}

PRIMARY_DIAGNOSES = (
    "PRETRAINED_REPRESENTATION_MISMATCH",
    "FINE_TUNING_DESTROYS_TRANSFER_GEOMETRY",
    "DATA_SCALE_INSUFFICIENT",
    "LABEL_SEMANTIC_SPECIFICATION_INSUFFICIENT",
    "MULTI_LABEL_COMPOSITION_SPARSITY",
    "TEXT_ONLY_SIGNAL_INSUFFICIENT",
    "MIXED_SIGNAL_AND_REPRESENTATION_FAILURE",
)

GOAL_HYPOTHESES = (
    "TEXT_SIGNAL_INSUFFICIENT",
    "LABEL_DESCRIPTION_INSUFFICIENT",
    "SUPERVISION_DENSITY_INSUFFICIENT",
    "PRETRAINED_REPRESENTATION_MISMATCH",
    "FINE_TUNING_DESTROYS_TRANSFER_GEOMETRY",
    "GOLD_CARDINALITY_OR_BOUNDARY_NOISE",
    "MIXED_SIGNAL_AND_REPRESENTATION_FAILURE",
)

DESCRIPTION_CLASSES = (
    "DESCRIPTION_SUFFICIENT",
    "DESCRIPTION_UNDERSPECIFIED",
    "DESCRIPTION_OVERBROAD",
    "DESCRIPTION_OVERLAPS_NEIGHBOR",
    "DESCRIPTION_REQUIRES_CONTEXT",
)

LEARNING_CURVE_CLASSES = (
    "DATA_LIMITED",
    "EARLY_SATURATION",
    "NEGATIVE_SCALING",
    "NO_LEARNING_SIGNAL",
)

PROBE_CLASSES = (
    "LINEARLY_AVAILABLE",
    "NONLINEARLY_AVAILABLE",
    "NOT_RECOVERABLE",
)

DESCRIPTION_VARIANTS = (
    "canonical_name",
    "canonical_full_definition",
    "positive_core",
    "definition_plus_exclusion",
)

ADAPTATION_REGIMES = (
    "A_ENCODER_FROZEN",
    "B_LAST_1_LAYER",
    "C_LAST_2_LAYERS",
    "D_FULL_FINETUNE",
)

LEARNING_FRACTIONS = (0.10, 0.25, 0.50, 0.75, 1.00)

ARCHITECTURE_RESTART_GATE = {
    "name": "V6_ARCHITECTURE_RESTART_GATE",
    "require_any": [
        "REP diagnostic > 0.20",
        "clear learning curve trajectory toward >0.20",
        "substantially improved label-separation margins with stable DEV→REP",
    ],
    "must_beat_zero_shot_reference": True,
    "zero_shot_reference": ZERO_SHOT_REFERENCE["rep_system_macro_f1"],
    "advancement_floor": ADVANCEMENT_GATE["min_rep_system_macro_f1"],
}


def reassessment_contract() -> dict[str, Any]:
    return {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "zero_shot_reference": ZERO_SHOT_REFERENCE,
        "advancement_floor_locked": True,
        "min_rep_system_macro_f1": ADVANCEMENT_GATE["min_rep_system_macro_f1"],
        "hierarchy_violation_floor": ADVANCEMENT_GATE[
            "max_hierarchy_violation_rate_rep"
        ],
        "forbidden": [
            "another_architecture_family_bakeoff",
            "lower_0.20_floor",
            "inspect_QUAL",
            "alter_ontology",
            "retune_against_REP_rows",
            "change_Stage_A_semantics",
            "choose_production_model",
            "create_new_qualification_surface",
        ],
        "description_variants": list(DESCRIPTION_VARIANTS),
        "adaptation_regimes": list(ADAPTATION_REGIMES),
        "learning_fractions": list(LEARNING_FRACTIONS),
        "primary_diagnoses": list(PRIMARY_DIAGNOSES),
        "goal_hypotheses": list(GOAL_HYPOTHESES),
        "architecture_restart_gate": ARCHITECTURE_RESTART_GATE,
        "label_descriptions_source": "HYPERLEX_V6_FAMILY_ONTOLOGY_V1_FINAL",
        "qual_policy": {
            "HYPERLEX_V6_QUALIFICATION_001": "REMAIN_SEALED",
            "inspected": False,
        },
    }


def classify_description_adequacy(label_id: str, text: str) -> dict[str, Any]:
    """Heuristic adequacy audit from frozen ontology wording only (no rewrite)."""
    t = text.lower()
    has_pos = any(
        k in t
        for k in (
            "evidence",
            "semantics",
            "framing",
            "judgment",
            "register",
            "community",
        )
    )
    has_excl = "exclusion" in t or "exclusions:" in t
    has_parent = "parent" in t or "child of" in t or "requires technology" in t
    # Broadness heuristic: very short or few content words after stripping boilerplate
    content = (
        t.replace("domain", "")
        .replace("function", "")
        .replace("mediation", "")
        .replace("exclusions:", "")
    )
    tokens = [w for w in content.split() if len(w) > 3]
    overbroad = len(tokens) < 8
    underspec = not has_excl or not has_pos
    requires_context = any(
        k in t
        for k in (
            "underdetermined",
            "insufficient_context",
            "mixed",
            "optional co-label",
        )
    )
    # Neighbor overlap: share distinctive stems with siblings
    overlaps = False
    sibs = []
    if label_id.startswith("domain."):
        sibs = [LABEL_DESCRIPTIONS[x] for x in DOMAIN_VOCAB if x != label_id]
    elif label_id.startswith("function."):
        sibs = [LABEL_DESCRIPTIONS[x] for x in FUNCTION_VOCAB if x != label_id]
    # crude: if positive-core noun appears in >2 siblings
    cores = [w for w in tokens if w not in {"without", "generic", "evidence", "sense"}]
    for w in cores[:5]:
        hits = sum(1 for s in sibs if w in s.lower())
        if hits >= 2:
            overlaps = True
            break

    if requires_context and underspec:
        klass = "DESCRIPTION_REQUIRES_CONTEXT"
    elif overlaps:
        klass = "DESCRIPTION_OVERLAPS_NEIGHBOR"
    elif overbroad:
        klass = "DESCRIPTION_OVERBROAD"
    elif underspec:
        klass = "DESCRIPTION_UNDERSPECIFIED"
    else:
        klass = "DESCRIPTION_SUFFICIENT"
    return {
        "label": label_id,
        "class": klass,
        "has_positive_criteria": has_pos,
        "has_negative_criteria": has_excl,
        "has_parent_context": has_parent,
        "overbroad_heuristic": overbroad,
        "overlaps_neighbor_heuristic": overlaps,
        "requires_context_heuristic": requires_context,
    }


def audit_all_descriptions() -> dict[str, Any]:
    defs = frozen_label_descriptions()
    per = {lab: classify_description_adequacy(lab, defs[lab]) for lab in defs}
    counts: dict[str, int] = {c: 0 for c in DESCRIPTION_CLASSES}
    for row in per.values():
        counts[row["class"]] = counts.get(row["class"], 0) + 1
    return {"per_label": per, "counts": counts, "n": len(per)}


def description_variants_for_label(label_id: str) -> dict[str, str]:
    """Preregistered semantically-equivalent wording variants (diagnostic only)."""
    full = LABEL_DESCRIPTIONS[label_id]
    # split on Exclusions
    if "Exclusions:" in full:
        core, excl = full.split("Exclusions:", 1)
        excl = "Exclusions:" + excl
    elif "Exclusions" in full:
        core, excl = full.split("Exclusions", 1)
        excl = "Exclusions" + excl
    else:
        core, excl = full, ""
    name = label_id.split(".")[-1].replace("_", " ")
    # positive-core: strip DOMAIN/FUNCTION prefix boilerplate before first colon content
    pos = core.strip()
    if ":" in pos:
        pos = pos.split(":", 1)[1].strip()
    return {
        "canonical_name": f"Label: {name}",
        "canonical_full_definition": full,
        "positive_core": pos,
        "definition_plus_exclusion": (core.strip() + " " + excl.strip()).strip(),
    }


def oracle_description(label_id: str) -> str:
    """Analysis-only oracle packing the full frozen boundary contract."""
    base = LABEL_DESCRIPTIONS[label_id]
    parent = None
    if label_id == "domain.technology.ai_discourse":
        parent = "domain.technology (required_parent)"
    axis = label_id.split(".")[0]
    neighbors = []
    vocab = (
        DOMAIN_VOCAB
        if axis == "domain"
        else FUNCTION_VOCAB
        if axis == "function"
        else MEDIATION_VOCAB
    )
    for other in vocab:
        if other == label_id:
            continue
        neighbors.append(other)
    return (
        f"{base} | PARENT: {parent or 'none'} | AXIS: {axis} | "
        f"ALLOWED_CO_LABELS: other axes when text-supported; "
        f"NEAR_NEIGHBORS_TO_DISTINGUISH: {', '.join(neighbors[:6])}; "
        f"GOLD_UNCHANGED: true; TEXT_ONLY_IDENTIFIABILITY: from ontology contract."
    )


def classify_learning_curve(points: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """points: [{fraction, rep_system_macro_f1}, ...] sorted by fraction."""
    if not points:
        return {"class": "NO_LEARNING_SIGNAL", "reason": "empty"}
    ys = [float(p["rep_system_macro_f1"]) for p in points]
    xs = [float(p["fraction"]) for p in points]
    y0, y1 = ys[0], ys[-1]
    # early saturation: last 2 within 0.01 and max < 0.20
    if len(ys) >= 2 and abs(ys[-1] - ys[-2]) < 0.01 and max(ys) < 0.20:
        klass = "EARLY_SATURATION"
    elif y1 + 0.01 < y0:
        klass = "NEGATIVE_SCALING"
    elif max(ys) < 0.05:
        klass = "NO_LEARNING_SIGNAL"
    elif y1 >= y0 + 0.03 and y1 < 0.20:
        klass = "DATA_LIMITED"
    elif y1 >= 0.20:
        klass = "DATA_LIMITED"  # still rising through floor
    else:
        klass = "EARLY_SATURATION"
    return {
        "class": klass,
        "y_at_10": y0 if xs and xs[0] <= 0.11 else None,
        "y_at_100": y1,
        "max": max(ys),
        "delta_10_to_100": y1 - y0,
        "points": list(points),
    }


def classify_probe(linear_f1: float, nonlinear_f1: float | None = None) -> str:
    if linear_f1 >= 0.20:
        return "LINEARLY_AVAILABLE"
    if nonlinear_f1 is not None and nonlinear_f1 >= 0.20:
        return "NONLINEARLY_AVAILABLE"
    if linear_f1 >= 0.10 or (nonlinear_f1 or 0) >= 0.10:
        return "NONLINEARLY_AVAILABLE" if (nonlinear_f1 or 0) > linear_f1 + 0.03 else "LINEARLY_AVAILABLE"
    return "NOT_RECOVERABLE"


def architecture_restart_allowed(
    *,
    best_diagnostic_rep: float,
    learning_curve: Mapping[str, Any] | None,
    margin_improved: bool,
    stable_gap: bool,
    beats_zero_shot: bool,
) -> dict[str, Any]:
    floor = ARCHITECTURE_RESTART_GATE["advancement_floor"]
    traj = False
    if learning_curve:
        pts = learning_curve.get("points") or []
        if len(pts) >= 2:
            ys = [float(p["rep_system_macro_f1"]) for p in pts]
            # clear trajectory: monotone-ish rise and last within 0.03 of floor or slope projects
            if ys[-1] > ys[0] + 0.04 and ys[-1] >= floor - 0.03:
                traj = True
            if learning_curve.get("class") == "DATA_LIMITED" and ys[-1] >= floor - 0.05:
                traj = True
    reasons = []
    if best_diagnostic_rep > floor:
        reasons.append("REP_DIAGNOSTIC_ABOVE_FLOOR")
    if traj:
        reasons.append("LEARNING_CURVE_TRAJECTORY")
    if margin_improved and stable_gap and beats_zero_shot:
        reasons.append("MARGIN_AND_STABLE_GENERALIZATION")
    allow = bool(reasons) and beats_zero_shot
    return {
        "allowed": allow,
        "reasons": reasons,
        "beats_zero_shot_reference": beats_zero_shot,
        "best_diagnostic_rep": best_diagnostic_rep,
        "zero_shot_reference": ZERO_SHOT_REFERENCE["rep_system_macro_f1"],
    }


def select_primary_diagnosis(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Map reassessment evidence bundle → primary + secondary + next action."""
    zs_ref = ZERO_SHOT_REFERENCE["rep_system_macro_f1"]
    strong = float(evidence.get("strong_semantic_rep") or 0.0)
    frozen_best = float(evidence.get("frozen_encoder_rep") or 0.0)
    full_ft = float(evidence.get("full_finetune_rep") or 0.0)
    curve = evidence.get("learning_curve") or {}
    desc_instability = bool(evidence.get("label_description_instability"))
    oracle_gain = float(evidence.get("oracle_gain") or 0.0)
    drift_catastrophic = bool(evidence.get("catastrophic_task_adaptation"))
    cardinality_primary = bool(evidence.get("failure_is_cardinality_driven"))
    composition_primary = bool(evidence.get("failure_is_composition_sparsity"))
    text_weak = bool(evidence.get("text_signal_insufficient"))
    axis_specific = bool(evidence.get("axis_specific_representations_justified"))

    secondary: list[str] = []
    primary = "MIXED_SIGNAL_AND_REPRESENTATION_FAILURE"
    next_action = "REASSESS_HYPERLEX_V6_TASK_DEFINITION"

    if strong >= 0.20:
        primary = "PRETRAINED_REPRESENTATION_MISMATCH"
        next_action = "REBASE_V6_ON_STRONGER_PRETRAINED_SEMANTIC_ENCODER"
    elif drift_catastrophic or (frozen_best > full_ft + 0.03 and frozen_best >= zs_ref - 0.02):
        primary = "FINE_TUNING_DESTROYS_TRANSFER_GEOMETRY"
        next_action = "DESIGN_PARAMETER_EFFICIENT_OR_FROZEN_V6_MODEL"
        if strong > zs_ref + 0.02:
            secondary.append("PRETRAINED_REPRESENTATION_MISMATCH")
    elif curve.get("class") == "DATA_LIMITED" and float(curve.get("y_at_100") or 0) >= 0.12:
        primary = "DATA_SCALE_INSUFFICIENT"
        next_action = "EXPAND_V6_NATURAL_SUPERVISION"
    elif desc_instability or oracle_gain >= 0.03:
        primary = "LABEL_SEMANTIC_SPECIFICATION_INSUFFICIENT"
        next_action = "REFINE_V6_LABEL_SEMANTIC_CONTRACTS"
    elif composition_primary:
        primary = "MULTI_LABEL_COMPOSITION_SPARSITY"
        next_action = "EXPAND_V6_NATURAL_SUPERVISION"
        secondary.append("DATA_SCALE_INSUFFICIENT")
    elif text_weak and strong < 0.18:
        primary = "TEXT_ONLY_SIGNAL_INSUFFICIENT"
        next_action = "REASSESS_HYPERLEX_V6_TASK_DEFINITION"
    elif strong < 0.18 and float(curve.get("max") or 0) < 0.18:
        primary = "TEXT_ONLY_SIGNAL_INSUFFICIENT"
        next_action = "REASSESS_HYPERLEX_V6_TASK_DEFINITION"
        secondary.append("MIXED_SIGNAL_AND_REPRESENTATION_FAILURE")
    else:
        primary = "MIXED_SIGNAL_AND_REPRESENTATION_FAILURE"
        next_action = "REASSESS_HYPERLEX_V6_TASK_DEFINITION"

    if cardinality_primary:
        secondary.append("GOLD_CARDINALITY_OR_BOUNDARY_NOISE")
    if axis_specific:
        secondary.append("AXIS_SPECIFIC_REPRESENTATIONS_JUSTIFIED")
    if frozen_best > full_ft + 0.02 and primary != "FINE_TUNING_DESTROYS_TRANSFER_GEOMETRY":
        secondary.append("FINE_TUNING_DESTROYS_TRANSFER_GEOMETRY")

    # Goal-hypothesis letter mapping
    goal_map = {
        "TEXT_ONLY_SIGNAL_INSUFFICIENT": "A. TEXT_SIGNAL_INSUFFICIENT",
        "LABEL_SEMANTIC_SPECIFICATION_INSUFFICIENT": "B. LABEL_DESCRIPTION_INSUFFICIENT",
        "DATA_SCALE_INSUFFICIENT": "C. SUPERVISION_DENSITY_INSUFFICIENT",
        "PRETRAINED_REPRESENTATION_MISMATCH": "D. PRETRAINED_REPRESENTATION_MISMATCH",
        "FINE_TUNING_DESTROYS_TRANSFER_GEOMETRY": "E. FINE_TUNING_DESTROYS_TRANSFER_GEOMETRY",
        "MULTI_LABEL_COMPOSITION_SPARSITY": "F. GOLD_CARDINALITY_OR_BOUNDARY_NOISE",
        "MIXED_SIGNAL_AND_REPRESENTATION_FAILURE": "G. MIXED_SIGNAL_AND_REPRESENTATION_FAILURE",
    }
    return {
        "primary_diagnosis": primary,
        "goal_hypothesis": goal_map.get(primary, primary),
        "secondary_contributors": sorted(set(secondary)),
        "NEXT_ACTION": next_action,
        "evidence_snapshot": {
            "strong_semantic_rep": strong,
            "frozen_encoder_rep": frozen_best,
            "full_finetune_rep": full_ft,
            "learning_curve_class": curve.get("class"),
            "oracle_gain": oracle_gain,
            "label_description_instability": desc_instability,
            "catastrophic_task_adaptation": drift_catastrophic,
        },
    }
