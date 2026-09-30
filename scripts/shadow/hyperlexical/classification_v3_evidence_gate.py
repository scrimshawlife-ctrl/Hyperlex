"""Classification v3 evidence-gate contracts and invariants.

Spec-only module for HYPERLEX_CLASSIFICATION_V3_EVIDENCE_GATE. Does not train,
does not score the spent v2 reserve, and does not move BEST.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

RULE = "HYPERLEX_CLASSIFICATION_V3_EVIDENCE_GATE"
LIFECYCLE_STATES = (
    "DRAFT",
    "PREREGISTERED",
    "READY",
    "RUNNING",
    "SETTLED_PASS",
    "SETTLED_FAIL",
    "SETTLED_INVALID",
)
CURRENT_STATE = "DRAFT"

EVIDENCE_LABELS = ("NO_EVIDENCE", "EVIDENCE_PRESENT", "UNCERTAIN")
EVIDENCE_SUBTYPES = (
    "POSITIVE_EVIDENCE",
    "HARD_NONE",
    "NEAR_DOMAIN_NONE",
    "GENERIC_NONE",
    "AMBIGUOUS_EVIDENCE",
)
DECISION_TYPES = ("NONE", "FAMILY", "ABSTAIN", "AMBIGUOUS")
REASON_CODES = (
    "NO_RELEVANT_EVIDENCE",
    "INSUFFICIENT_EVIDENCE_CONFIDENCE",
    "INSUFFICIENT_FAMILY_SUPPORT",
    "MULTIPLE_FAMILIES_SUPPORTED",
    "SINGLE_FAMILY_SUPPORTED",
)

SUBTYPE_TO_LABEL = {
    "POSITIVE_EVIDENCE": "EVIDENCE_PRESENT",
    "HARD_NONE": "NO_EVIDENCE",
    "NEAR_DOMAIN_NONE": "NO_EVIDENCE",
    "GENERIC_NONE": "NO_EVIDENCE",
    "AMBIGUOUS_EVIDENCE": "UNCERTAIN",
}

# Preregistered before results. Not derived from spent v2 reserve.
FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX = 0.05
FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE = 0.80

V2_SETTLEMENT = {
    "HYPERLEX_CLASSIFICATION_V2": "RESERVE_FAILED",
    "primary_failure": "APPLICABILITY_GENERALIZATION_FAILURE",
    "family_retrieval": "VALIDATION_SUPPORTED_RESERVE_UNSUPPORTED",
    "production_promotion": "REJECTED",
    "BEST": "UNCHANGED",
    "best_sha256": "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6",
    "spent_v2_reserve_reuse": False,
}

PROHIBITIONS = (
    "forced_18_way_argmax_as_semantic_truth",
    "reserve_derived_thresholds",
    "per_family_validation_threshold_tuning",
    "class_weight_experimentation_loops",
    "prototype_only_family_semantics",
    "family_retrieval_to_compensate_for_bad_evidence_gating",
    "uncertain_mapped_to_evidence_present",
    "stage_b_without_evidence_present",
    "spent_v2_reserve_for_train_val_or_promotion",
)


class EvidenceGateContractError(ValueError):
    """Invariant failure for Classification v3 evidence-gate contracts."""


def evidence_gate_contract() -> dict[str, Any]:
    return {
        "current_state": CURRENT_STATE,
        "false_evidence_entry_rate_on_none_max": FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
        "family_emission_precision_min_after_gate": FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE,
        "lifecycle_states": list(LIFECYCLE_STATES),
        "prohibitions": list(PROHIBITIONS),
        "rule": RULE,
        "spent_v2_reserve_reuse": False,
        "train": False,
        "v2_settlement": dict(V2_SETTLEMENT),
    }


def subtype_label(subtype: str) -> str:
    if subtype not in SUBTYPE_TO_LABEL:
        raise EvidenceGateContractError(f"unknown_subtype:{subtype}")
    return SUBTYPE_TO_LABEL[subtype]


def validate_example_label_pair(evidence_label: str, evidence_subtype: str) -> None:
    expected = subtype_label(evidence_subtype)
    if evidence_label != expected:
        raise EvidenceGateContractError(
            f"subtype_label_mismatch:{evidence_subtype}->{evidence_label}!={expected}"
        )


def decide_evidence(
    evidence_score: float,
    *,
    none_threshold: float,
    present_threshold: float,
) -> str:
    if not (0.0 <= float(evidence_score) <= 1.0):
        raise EvidenceGateContractError("evidence_score_out_of_range")
    if not (0.0 <= float(none_threshold) < float(present_threshold) <= 1.0):
        raise EvidenceGateContractError("threshold_order_invalid")
    if float(evidence_score) >= float(present_threshold):
        return "EVIDENCE_PRESENT"
    if float(evidence_score) <= float(none_threshold):
        return "NO_EVIDENCE"
    return "UNCERTAIN"


def may_invoke_retrieval(evidence_decision: str) -> bool:
    if evidence_decision not in EVIDENCE_LABELS:
        raise EvidenceGateContractError(f"unknown_evidence_decision:{evidence_decision}")
    return evidence_decision == "EVIDENCE_PRESENT"


def require_retrieval_allowed(evidence_decision: str) -> None:
    if not may_invoke_retrieval(evidence_decision):
        raise EvidenceGateContractError(
            f"retrieval_forbidden_for:{evidence_decision}"
        )


def validate_probability_vector(probabilities: Mapping[str, float], *, tol: float = 1e-6) -> None:
    if set(probabilities) != set(EVIDENCE_LABELS):
        raise EvidenceGateContractError("probability_keys_invalid")
    total = 0.0
    for key in EVIDENCE_LABELS:
        value = float(probabilities[key])
        if not math.isfinite(value) or value < 0.0 or value > 1.0:
            raise EvidenceGateContractError(f"probability_invalid:{key}")
        total += value
    if abs(total - 1.0) > tol:
        raise EvidenceGateContractError("probability_sum_invalid")


def map_stage_a_to_end_to_end(evidence_decision: str) -> str | None:
    """Immediate terminal mapping, or None if Stage B must run."""
    if evidence_decision == "NO_EVIDENCE":
        return "NONE"
    if evidence_decision == "UNCERTAIN":
        return "ABSTAIN"
    if evidence_decision == "EVIDENCE_PRESENT":
        return None
    raise EvidenceGateContractError(f"unknown_evidence_decision:{evidence_decision}")


def compose_decision(
    *,
    evidence_decision: str,
    candidates: Sequence[Mapping[str, Any]] | None = None,
    family_score_min: float = 0.0,
    family_margin_min: float = 0.0,
) -> dict[str, Any]:
    """Deterministic Stage A/B/C composition for contract tests (no model)."""
    terminal = map_stage_a_to_end_to_end(evidence_decision)
    if terminal == "NONE":
        return {
            "decision_type": "NONE",
            "family": None,
            "reason_code": "NO_RELEVANT_EVIDENCE",
        }
    if terminal == "ABSTAIN":
        return {
            "decision_type": "ABSTAIN",
            "family": None,
            "reason_code": "INSUFFICIENT_EVIDENCE_CONFIDENCE",
        }
    require_retrieval_allowed(evidence_decision)
    rows = list(candidates or [])
    if not rows:
        return {
            "decision_type": "ABSTAIN",
            "family": None,
            "reason_code": "INSUFFICIENT_FAMILY_SUPPORT",
        }
    ordered = sorted(
        rows,
        key=lambda item: (-float(item["score"]), str(item["family"])),
    )
    top = ordered[0]
    second_score = float(ordered[1]["score"]) if len(ordered) > 1 else float("-inf")
    margin = float(top["score"]) - second_score
    if float(top["score"]) < float(family_score_min):
        return {
            "decision_type": "ABSTAIN",
            "family": None,
            "reason_code": "INSUFFICIENT_FAMILY_SUPPORT",
        }
    if len(ordered) > 1 and margin < float(family_margin_min):
        return {
            "decision_type": "AMBIGUOUS",
            "family": None,
            "candidate_families": [str(item["family"]) for item in ordered[:3]],
            "reason_code": "MULTIPLE_FAMILIES_SUPPORTED",
        }
    return {
        "decision_type": "FAMILY",
        "family": str(top["family"]),
        "family_score": float(top["score"]),
        "family_margin": margin if math.isfinite(margin) else None,
        "reason_code": "SINGLE_FAMILY_SUPPORTED",
    }


def validate_end_to_end_invariants(decision: Mapping[str, Any], evidence_decision: str) -> None:
    decision_type = decision.get("decision_type")
    if decision_type not in DECISION_TYPES:
        raise EvidenceGateContractError("decision_type_invalid")
    if decision_type == "NONE":
        if evidence_decision != "NO_EVIDENCE":
            raise EvidenceGateContractError("none_requires_no_evidence")
        if decision.get("family") is not None:
            raise EvidenceGateContractError("none_family_not_null")
    if decision_type == "FAMILY":
        if evidence_decision != "EVIDENCE_PRESENT":
            raise EvidenceGateContractError("family_requires_evidence_present")
        if not decision.get("family"):
            raise EvidenceGateContractError("family_missing")
    if decision_type == "AMBIGUOUS":
        if evidence_decision != "EVIDENCE_PRESENT":
            raise EvidenceGateContractError("ambiguous_requires_evidence_present")
    if decision_type == "ABSTAIN":
        if evidence_decision not in {"UNCERTAIN", "EVIDENCE_PRESENT"}:
            raise EvidenceGateContractError("abstain_origin_invalid")


def refuse_spent_reserve_identity(identity: str, spent_reserve_ids: Sequence[str]) -> None:
    if identity in set(spent_reserve_ids):
        raise EvidenceGateContractError("spent_v2_reserve_identity_forbidden")


def candidates_in_ontology(
    candidates: Sequence[Mapping[str, Any]], ontology: Sequence[str]
) -> None:
    allowed = set(ontology)
    for row in candidates:
        family = str(row.get("family") or "")
        if family not in allowed:
            raise EvidenceGateContractError(f"family_outside_ontology:{family}")
