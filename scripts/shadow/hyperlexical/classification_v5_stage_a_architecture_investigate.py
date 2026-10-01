"""ARCHITECTURE_OR_OBJECTIVE_INVESTIGATION — Stage-A-004 / V1R9 helpers.

Read-only analysis helpers. No train, no dataset mutation, no BEST move.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Mapping, Sequence

INVESTIGATE_RULE = "ARCHITECTURE_OR_OBJECTIVE_INVESTIGATION"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V5-STAGE-A-004"
PARENT_EXPERIMENT = "HLX-CLASSIFICATION-V5-STAGE-A-002"
PARENT_DATASET_SHA = (
    "c0fdd82d1734585a7d852318ac5b390cc5e2c50908c0ef9f9eba4b3f7ebedc8b"
)
DATASET_SHA = "8d4be8301b89b191841342fe11ef647c838b32e56e6d133b610c232264c5d00a"
SELECTED_SHA = "82840630a89ea9e9b34fdfc010d455e6bbfce05ecfcb29abe2929505e9e21fdd"
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
SURFACE_RULE = "HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R9"
DIAG_NONE = 0.50
DIAG_PRESENT = 0.55

PRIMARY_DECISIONS = (
    "STAGE_A_OBJECTIVE_SUFFICIENT",
    "STAGE_A_HEAD_LIMITED",
    "STAGE_A_REPRESENTATION_LIMITED",
    "STAGE_A_OBJECTIVE_MISMATCH",
    "STAGE_A_ARCHITECTURE_REDESIGN_REQUIRED",
)

BOTTLENECKS = (
    "HEAD_LIMITED",
    "REPRESENTATION_LIMITED",
    "OBJECTIVE_LIMITED",
    "MIXED",
)

SEPARABILITY = ("SEPARABLE", "PARTIALLY_SEPARABLE", "COLLAPSED")

FN_MODES = (
    "PRESENT_TO_NONE",
    "PRESENT_TO_UNCERTAIN",
    "LOW_CONFIDENCE",
    "THRESHOLD_FAILURE",
    "REPRESENTATION_FAILURE",
    "FEATURE_ABSENCE",
)


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        xf = float(x)
        yf = float(y)
        dot += xf * yf
        na += xf * xf
        nb += yf * yf
    denom = math.sqrt(na) * math.sqrt(nb)
    if denom <= 0.0:
        return 0.0
    return dot / denom


def mean_vector(vectors: Sequence[Sequence[float]]) -> list[float] | None:
    if not vectors:
        return None
    dim = len(vectors[0])
    acc = [0.0] * dim
    for vec in vectors:
        for i, value in enumerate(vec):
            acc[i] += float(value)
    n = float(len(vectors))
    return [value / n for value in acc]


def classify_separability(
    *,
    present_none_centroid_cosine: float | None,
    present_uncertain_centroid_cosine: float | None,
    present_fn_nearest_none_frac: float | None,
    present_fn_nearest_present_frac: float | None,
) -> str:
    """Map embedding geometry to SEPARABLE / PARTIALLY_SEPARABLE / COLLAPSED."""
    pn = present_none_centroid_cosine
    pu = present_uncertain_centroid_cosine
    fn_none = present_fn_nearest_none_frac
    fn_present = present_fn_nearest_present_frac
    if pn is None or fn_none is None:
        return "PARTIALLY_SEPARABLE"
    # High centroid overlap + FN nearest-NONE dominance → collapsed.
    if pn >= 0.92 and fn_none >= 0.60:
        return "COLLAPSED"
    if pn >= 0.85 and (fn_none or 0) >= 0.45:
        return "PARTIALLY_SEPARABLE"
    if pn <= 0.75 and (fn_present or 0) >= 0.55 and (pu is None or pu <= 0.90):
        return "SEPARABLE"
    return "PARTIALLY_SEPARABLE"


def classify_present_fn_mode(row: Mapping[str, Any]) -> str:
    """Classify one PRESENT false-negative under sealed diagnostic thresholds."""
    decision = str(row["decision"])
    p_present = float(row["P_EVIDENCE_PRESENT"])
    p_none = float(row["P_NO_EVIDENCE"])
    p_unc = float(row["P_UNCERTAIN"])
    nearest = str(row.get("nearest_centroid") or "")
    feature_absent = bool(row.get("feature_absence"))

    if decision == "UNCERTAIN":
        base = "PRESENT_TO_UNCERTAIN"
    else:
        base = "PRESENT_TO_NONE"

    if feature_absent:
        return "FEATURE_ABSENCE"
    if nearest == "NO_EVIDENCE" and p_none >= 0.80 and p_present <= 0.20:
        return "REPRESENTATION_FAILURE"
    # Near diagnostic band but decided non-PRESENT → threshold policy.
    if DIAG_NONE < p_present < DIAG_PRESENT:
        return "THRESHOLD_FAILURE"
    if p_present < 0.35 and max(p_none, p_unc) >= 0.55:
        return "LOW_CONFIDENCE" if p_present >= 0.15 else base
    if base == "PRESENT_TO_UNCERTAIN":
        return "PRESENT_TO_UNCERTAIN"
    return "PRESENT_TO_NONE"


def classify_bottleneck(
    *,
    separability: str,
    present_fn_profile: str,
    uncertain_decision_ignore_frac: float | None,
    focal_already_falsified: bool,
) -> str:
    if separability == "COLLAPSED":
        return "REPRESENTATION_LIMITED"
    if present_fn_profile == "NEAR_BOUNDARY" and separability == "SEPARABLE":
        return "HEAD_LIMITED"
    if (
        present_fn_profile in {"CONFIDENT_NONE", "CONFIDENT_NONE_LEANING"}
        and separability in {"SEPARABLE", "PARTIALLY_SEPARABLE"}
        and focal_already_falsified
    ):
        # Easy-NONE objective pressure alone already falsified; residual is
        # abstraction/policy (flat 3-way + P(PRESENT)-only decide).
        if (uncertain_decision_ignore_frac or 0) >= 0.40:
            return "MIXED"
        return "OBJECTIVE_LIMITED"
    if present_fn_profile in {"CONFIDENT_NONE", "CONFIDENT_NONE_LEANING"}:
        return "OBJECTIVE_LIMITED"
    return "MIXED"


def choose_primary_decision(
    *,
    bottleneck: str,
    separability: str,
    present_fn_profile: str,
    focal_already_falsified: bool,
    uncertain_policy_invisible: bool,
    dataset_change_justified: bool,
) -> dict[str, Any]:
    """Return exactly one PRIMARY_DECISIONS value + remediation flags."""
    if dataset_change_justified:
        # Should not happen for Stage-A-004 residual path; keep fail-closed.
        primary = "STAGE_A_OBJECTIVE_SUFFICIENT"
        arch = False
        data = True
        new_exp = False
        next_action = "HOLD_DATASET_CHANGE_NOT_INDICATED"
    elif bottleneck == "REPRESENTATION_LIMITED" or separability == "COLLAPSED":
        primary = "STAGE_A_REPRESENTATION_LIMITED"
        arch = True
        data = False
        new_exp = False
        next_action = "DESIGN_V5_STAGE_A_ARCHITECTURE_REDESIGN_SPEC"
    elif bottleneck == "HEAD_LIMITED":
        primary = "STAGE_A_HEAD_LIMITED"
        arch = True
        data = False
        new_exp = False
        next_action = "DESIGN_V5_STAGE_A_ARCHITECTURE_REDESIGN_SPEC"
    elif (
        focal_already_falsified
        and uncertain_policy_invisible
        and present_fn_profile in {"CONFIDENT_NONE", "CONFIDENT_NONE_LEANING", "MIXED_OR_SOFT"}
    ):
        # Flat 3-way CE + P(PRESENT)-only decide is the wrong abstraction after
        # dataset remediation and focal falsification.
        primary = "STAGE_A_ARCHITECTURE_REDESIGN_REQUIRED"
        arch = True
        data = False
        new_exp = False
        next_action = "DESIGN_V5_STAGE_A_ARCHITECTURE_REDESIGN_SPEC"
    elif bottleneck == "OBJECTIVE_LIMITED" and not focal_already_falsified:
        primary = "STAGE_A_OBJECTIVE_MISMATCH"
        arch = False
        data = False
        new_exp = True
        next_action = "HOLD_OBJECTIVE_EXPERIMENT_CLEAR"
    elif bottleneck == "OBJECTIVE_LIMITED" and focal_already_falsified:
        primary = "STAGE_A_ARCHITECTURE_REDESIGN_REQUIRED"
        arch = True
        data = False
        new_exp = False
        next_action = "DESIGN_V5_STAGE_A_ARCHITECTURE_REDESIGN_SPEC"
    else:
        primary = "STAGE_A_OBJECTIVE_MISMATCH"
        arch = True
        data = False
        new_exp = False
        next_action = "DESIGN_V5_STAGE_A_ARCHITECTURE_REDESIGN_SPEC"

    return {
        "PRIMARY_DECISION": primary,
        "architecture_change_required": arch,
        "dataset_change_required": data,
        "new_experiment_required": new_exp,
        "NEXT_ACTION": next_action,
        "bottleneck": bottleneck,
        "separability": separability,
    }


def architecture_alternative_cards() -> list[dict[str, Any]]:
    """Compare A/B/C without selecting a winner to train."""
    return [
        {
            "id": "A_MULTITASK_PRESENT_DETECTOR",
            "summary": (
                "Shared encoder; multi-task evidence head with an explicit "
                "PRESENT detector; family decision downstream."
            ),
            "expected_failure_mode": (
                "PRESENT detector may over-fire on ordinary NONE if not "
                "regularized; family head still needs Stage-A gates held."
            ),
            "implementation_complexity": "MEDIUM",
            "compatibility": (
                "Compatible with frozen V1R9 surface and BEST base; changes "
                "head graph + loss terms only."
            ),
            "evidence_requirement": (
                "Needs PRESENT-FN embedding nearest-PRESENT rate and residual "
                "NONE conservatism after detector-style scoring."
            ),
            "reversible": True,
        },
        {
            "id": "B_TWO_STAGE",
            "summary": (
                "Stage 1: NO_EVIDENCE vs EVIDENCE_PRESENT; Stage 2: UNCERTAIN "
                "vs CONFIRMED_PRESENT given evidence."
            ),
            "expected_failure_mode": (
                "Stage-1 NONE conservatism can still bury PRESENT; Stage-2 "
                "cannot recover PRESENT→NONE from Stage-1."
            ),
            "implementation_complexity": "MEDIUM",
            "compatibility": (
                "Ontology-compatible with epistemic UNCERTAIN; decide_evidence "
                "P(PRESENT)-only policy is replaced by staged decisions."
            ),
            "evidence_requirement": (
                "Supported when UNCERTAIN mass exists but decision ignores it, "
                "and PRESENT→NONE are not exclusively representation-collapsed."
            ),
            "reversible": True,
        },
        {
            "id": "C_CURRENT_3CLASS",
            "summary": "Current flat 3-class linear head + P(PRESENT)-only thresholds.",
            "expected_failure_mode": (
                "NONE dominance + ignored P(UNCERTAIN) + PRESENT FN deep in "
                "NONE; threshold grid remains empty."
            ),
            "implementation_complexity": "NONE",
            "compatibility": "Status quo; already SETTLED_FAIL after remediating + focal.",
            "evidence_requirement": "Falsified as sufficient by Stage-A-003/004 chain.",
            "reversible": True,
        },
    ]


def smallest_reversible_redesign(
    *,
    primary: str,
    bottleneck: str,
    uncertain_policy_invisible: bool,
    separability: str,
) -> dict[str, Any]:
    """Define smallest reversible change without authorizing a train."""
    if primary in {
        "STAGE_A_ARCHITECTURE_REDESIGN_REQUIRED",
        "STAGE_A_HEAD_LIMITED",
    } or (uncertain_policy_invisible and separability != "COLLAPSED"):
        return {
            "change_id": "B_TWO_STAGE_DECISION_GRAPH",
            "description": (
                "Replace flat 3-way decide_evidence(P_PRESENT) with a reversible "
                "two-stage decision graph on the same encoder: "
                "(1) NO_EVIDENCE vs EVIDENCE_CANDIDATE; "
                "(2) UNCERTAIN vs CONFIRMED_PRESENT given candidate. "
                "Keep V1R9 / BEST / seed frozen. Spec-only until CLEAR."
            ),
            "why_smallest": (
                "Does not require backbone change or new surface acquisition; "
                "directly addresses P(UNCERTAIN)-ignored policy and PRESENT "
                "vs NONE gate coupling under one softmax."
            ),
            "train_authorized": False,
            "dataset_change": False,
            "alternatives_considered": ["A_MULTITASK_PRESENT_DETECTOR", "C_CURRENT_3CLASS"],
            "note": "Comparison only — no winner authorized for training in this step.",
        }
    if primary == "STAGE_A_REPRESENTATION_LIMITED" or separability == "COLLAPSED":
        return {
            "change_id": "A_MULTITASK_PRESENT_DETECTOR",
            "description": (
                "Add an explicit PRESENT detector head on the shared encoder "
                "(multi-task), leaving family decision downstream. Spec-only "
                "until CLEAR; no backbone swap."
            ),
            "why_smallest": (
                "Targets representation→PRESENT collapse without discarding "
                "the encoder; reversible by removing the detector head."
            ),
            "train_authorized": False,
            "dataset_change": False,
            "alternatives_considered": ["B_TWO_STAGE", "C_CURRENT_3CLASS"],
            "note": "Comparison only — no winner authorized for training in this step.",
        }
    return {
        "change_id": "NONE_HOLD",
        "description": "No architecture redesign authorized; hold for CLEAR.",
        "why_smallest": "Evidence does not yet force a redesign commit.",
        "train_authorized": False,
        "dataset_change": False,
        "alternatives_considered": ["A_MULTITASK_PRESENT_DETECTOR", "B_TWO_STAGE", "C_CURRENT_3CLASS"],
        "note": "No train.",
    }


def decompose_fn_modes(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    modes = Counter(classify_present_fn_mode(row) for row in rows)
    total = max(1, len(rows))
    return {
        "n": len(rows),
        "counts": {mode: int(modes.get(mode, 0)) for mode in FN_MODES},
        "percentages": {
            mode: float(modes.get(mode, 0)) / total for mode in FN_MODES
        },
    }
