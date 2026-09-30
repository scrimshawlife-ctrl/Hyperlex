"""AUDIT_V5_UNCERTAIN_LABEL_SURFACE — fail-closed audit contract helpers.

Absence of evidence in the dataset is not evidence for NO_EVIDENCE.
Missing metadata is never a semantic label.
"""

from __future__ import annotations

from typing import Any, Mapping

RULE_ID = "AUDIT_V5_UNCERTAIN_LABEL_SURFACE"
SCHEMA = "hyperlex.classification.v5.stage_a_uncertain_label_surface_audit.v1"
GOLD_MAPPING_RULE = "HYPERLEX_V5_STAGE_A_GOLD_LABEL_MAPPING_V1"

MISSING_FIELD = "MISSING_FIELD"
NO_DATA = "NO_DATA"
NOT_APPLICABLE = "NOT_APPLICABLE"
NOT_COMPUTABLE = "NOT_COMPUTABLE"
OBSERVED_VALUE = "OBSERVED_VALUE"

FROZEN_AMBIGUITY_REASONS = (
    "INSUFFICIENT_CONTEXT",
    "CONFLICTING_EVIDENCE",
    "PARTIAL_REQUIRED_CORE",
    "MULTIPLE_PLAUSIBLE_INTERPRETATIONS",
    "UNRESOLVED_SOURCE_MEANING",
)

REQUIRED_UNCERTAIN_FIELDS = (
    "identity",
    "text",
    "evidence_subtype",
    "gold_label",
    "required_evidence_present",
    "ambiguity_reason",
    "source_provenance",
    "label_authority",
    "label_derivation",
    "reviewer_state",
    "source_identity",
    "source_sha256",
    "split",
)

OPTIONAL_FIELDS = (
    "active_family_support",
    "paired_identities",
    "domain",
    "definition_style",
    "evidence_spans",
    "nearest_present_identity",
    "nearest_none_identity",
)

BOUNDARY_CLASSES = ("CENTERED_BETWEEN", "PRESENT_LIKE", "NONE_LIKE", "ISOLATED")
GOLD_FLAGS = (
    "SEMANTICALLY_CLEAN",
    "TOO_PRESENT_LIKE",
    "TOO_NONE_LIKE",
    "REASON_UNDERDEFINED",
    "CONTEXT_INSUFFICIENT_TO_AUDIT",
)

PROB_TOLERANCE = 1e-3


def field_state(value: Any) -> str:
    if value is None:
        return MISSING_FIELD
    if isinstance(value, str) and value.strip() == "":
        return MISSING_FIELD
    return OBSERVED_VALUE


def extract_ambiguity_reason(
    row: Mapping[str, Any], label_provenance: Mapping[str, Any] | None
) -> tuple[Any, str]:
    """Return (reason_or_None, state). Never invent a reason."""
    if isinstance(row.get("ambiguity_reason"), str):
        reason = row["ambiguity_reason"]
        if reason in FROZEN_AMBIGUITY_REASONS:
            return reason, OBSERVED_VALUE
        return reason, "INVALID_REASON"
    # Explicit stored path only via label_provenance.evidence_basis[].ambiguity_reason
    if label_provenance:
        for item in label_provenance.get("evidence_basis") or []:
            if isinstance(item, Mapping) and "ambiguity_reason" in item:
                reason = item.get("ambiguity_reason")
                if reason in FROZEN_AMBIGUITY_REASONS:
                    return reason, OBSERVED_VALUE
                return reason, "INVALID_REASON"
    return None, MISSING_FIELD


def required_field_bundle(
    row: Mapping[str, Any],
    *,
    label_provenance: Mapping[str, Any] | None,
    source_provenance: Any,
) -> dict[str, Any]:
    reason, reason_state = extract_ambiguity_reason(row, label_provenance)
    lp = label_provenance or {}
    bundled = {
        "identity": row.get("identity"),
        "text": row.get("text"),
        "evidence_subtype": row.get("evidence_subtype"),
        "gold_label": row.get("evidence_label"),
        "required_evidence_present": row.get("required_evidence_present"),
        "ambiguity_reason": reason,
        "source_provenance": source_provenance
        if source_provenance is not None
        else row.get("provenance"),
        "label_authority": lp.get("authority"),
        "label_derivation": lp.get("derivation"),
        "reviewer_state": lp.get("reviewer_state"),
        "source_identity": row.get("source_bucket"),
        "source_sha256": row.get("source_sha256"),
        "split": row.get("split"),
    }
    states = {k: field_state(v) for k, v in bundled.items()}
    # ambiguity_reason uses dedicated state
    states["ambiguity_reason"] = reason_state if reason_state != OBSERVED_VALUE else field_state(reason)
    missing = [k for k, st in states.items() if st != OBSERVED_VALUE]
    audit_row_state = MISSING_FIELD if missing else "COMPLETE"
    return {
        "fields": bundled,
        "field_states": states,
        "missing_required_fields": missing,
        "audit_row_state": audit_row_state,
        "ambiguity_reason_state": states["ambiguity_reason"],
    }


def gold_consistency_flag(
    *,
    audit_row_state: str,
    fields: Mapping[str, Any],
    boundary_class: str | None,
    boundary_state: str,
) -> str:
    if audit_row_state == MISSING_FIELD and "ambiguity_reason" in (
        # caller passes missing list indirectly via fields
    ):
        pass
    if fields.get("ambiguity_reason") is None or fields.get("ambiguity_reason") not in FROZEN_AMBIGUITY_REASONS:
        if fields.get("gold_label") == "UNCERTAIN":
            return "REASON_UNDERDEFINED"
    if (
        fields.get("evidence_subtype") != "AMBIGUOUS_EVIDENCE"
        or fields.get("gold_label") != "UNCERTAIN"
        or str(fields.get("required_evidence_present")) != "uncertain"
    ):
        return "REASON_UNDERDEFINED"
    if boundary_state == NOT_COMPUTABLE:
        return "CONTEXT_INSUFFICIENT_TO_AUDIT"
    if boundary_class == "PRESENT_LIKE":
        return "TOO_PRESENT_LIKE"
    if boundary_class == "NONE_LIKE":
        return "TOO_NONE_LIKE"
    if boundary_class in {"CENTERED_BETWEEN", "ISOLATED"}:
        return "SEMANTICALLY_CLEAN"
    return "CONTEXT_INSUFFICIENT_TO_AUDIT"


def classify_boundary(
    nearest_present_cosine: float | None,
    nearest_none_cosine: float | None,
) -> tuple[str | None, str]:
    if nearest_present_cosine is None or nearest_none_cosine is None:
        return None, NOT_COMPUTABLE
    margin = float(nearest_present_cosine) - float(nearest_none_cosine)
    # Diagnostic thresholds (frozen for this audit; not production decision policy).
    if abs(margin) <= 0.02 and max(nearest_present_cosine, nearest_none_cosine) >= 0.70:
        return "CENTERED_BETWEEN", OBSERVED_VALUE
    if nearest_present_cosine >= 0.85 and margin >= 0.05:
        return "PRESENT_LIKE", OBSERVED_VALUE
    if nearest_none_cosine >= 0.85 and margin <= -0.05:
        return "NONE_LIKE", OBSERVED_VALUE
    if max(nearest_present_cosine, nearest_none_cosine) < 0.60:
        return "ISOLATED", OBSERVED_VALUE
    if margin > 0:
        return "PRESENT_LIKE", OBSERVED_VALUE
    if margin < 0:
        return "NONE_LIKE", OBSERVED_VALUE
    return "CENTERED_BETWEEN", OBSERVED_VALUE


def valid_probabilities(probs: Mapping[str, Any] | None) -> tuple[dict[str, float] | None, str]:
    if not probs:
        return None, "INVALID_OR_MISSING"
    try:
        p_none = float(probs["P_NO_EVIDENCE"])
        p_pres = float(probs["P_EVIDENCE_PRESENT"])
        p_unc = float(probs["P_UNCERTAIN"])
    except (KeyError, TypeError, ValueError):
        return None, "INVALID_OR_MISSING"
    if not all(map(lambda x: x == x and abs(x) != float("inf"), (p_none, p_pres, p_unc))):
        return None, "INVALID_OR_MISSING"
    if abs((p_none + p_pres + p_unc) - 1.0) > PROB_TOLERANCE:
        return None, "INVALID_OR_MISSING"
    return {
        "P_NO_EVIDENCE": p_none,
        "P_EVIDENCE_PRESENT": p_pres,
        "P_UNCERTAIN": p_unc,
    }, OBSERVED_VALUE


def metric_with_denominator(
    value: Any,
    *,
    n_eligible: int,
    n_excluded_missing: int = 0,
    n_excluded_invalid: int = 0,
    state: str = OBSERVED_VALUE,
) -> dict[str, Any]:
    return {
        "value": value,
        "n_eligible": n_eligible,
        "n_excluded_missing": n_excluded_missing,
        "n_excluded_invalid": n_excluded_invalid,
        "state": state,
    }


def coverage(n_metric_eligible: int, n_cohort_total: int) -> dict[str, Any]:
    if n_cohort_total <= 0:
        return {
            "coverage": NO_DATA,
            "n_metric_eligible": 0,
            "n_cohort_total": 0,
            "aggregate_state": NO_DATA,
        }
    cov = n_metric_eligible / n_cohort_total
    return {
        "coverage": cov,
        "n_metric_eligible": n_metric_eligible,
        "n_cohort_total": n_cohort_total,
        "aggregate_state": "LOW_COVERAGE" if cov < 0.80 else "OK",
    }


def reason_support_table(train_counts: Mapping[str, int], val_counts: Mapping[str, int]) -> dict[str, Any]:
    out = {}
    for reason in FROZEN_AMBIGUITY_REASONS:
        tr = int(train_counts.get(reason, 0))
        va = int(val_counts.get(reason, 0))
        flags = []
        if tr < 25:
            flags.append("UNDER_SUPPORTED_REASON")
        if va < 10:
            flags.append("UNDER_SUPPORTED_REASON")
        out[reason] = {
            "train_support": tr,
            "validation_support": va,
            "reason_state": NO_DATA if (tr == 0 and va == 0) else OBSERVED_VALUE,
            "flags": sorted(set(flags)),
        }
    return out


def data_completeness_blocks_clean(
    *,
    uncertain_missing_required_frac: float,
    probability_coverage: float | str,
    representation_coverage: float | str,
    ambiguity_reason_coverage: float | str,
) -> bool:
    def _lt(value: float | str, thresh: float) -> bool:
        if isinstance(value, str):
            return True
        return float(value) < thresh

    if uncertain_missing_required_frac > 0.05:
        return True
    if _lt(probability_coverage, 0.80):
        return True
    if _lt(representation_coverage, 0.80):
        return True
    if _lt(ambiguity_reason_coverage, 0.95):
        return True
    return False


def decide_diagnosis(
    *,
    data_completeness_blocker: bool,
    under_supported_reasons: list[str],
    boundary_conflict: bool,
    source_skew: bool,
    mixed_surface_issues: bool,
    clean_enough: bool,
) -> tuple[str, str]:
    if data_completeness_blocker:
        return "MIXED_UNCERTAIN_SURFACE_FAILURE", "REMEDIATE_V5_UNCERTAIN_SURFACE"
    # Priority: boundary conflict > under-supported > source skew > mixed > clean
    if boundary_conflict:
        return "UNCERTAIN_BOUNDARY_CONFLICT", "REDEFINE_V5_UNCERTAIN_GOLD_BOUNDARY"
    if under_supported_reasons:
        return "UNCERTAIN_SURFACE_UNDER_SUPPORTED", "EXPAND_V5_UNCERTAIN_SURFACE"
    if source_skew:
        return "UNCERTAIN_SOURCE_SKEW", "REBALANCE_V5_UNCERTAIN_SURFACE"
    if mixed_surface_issues:
        return "MIXED_UNCERTAIN_SURFACE_FAILURE", "REMEDIATE_V5_UNCERTAIN_SURFACE"
    if clean_enough:
        return "UNCERTAIN_SURFACE_CLEAN", "STOP_AND_REVISIT_STAGE_A_REPRESENTATION"
    return "MIXED_UNCERTAIN_SURFACE_FAILURE", "REMEDIATE_V5_UNCERTAIN_SURFACE"
