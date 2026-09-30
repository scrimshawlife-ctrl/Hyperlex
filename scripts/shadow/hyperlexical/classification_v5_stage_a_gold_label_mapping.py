"""HYPERLEX_V5_STAGE_A_GOLD_LABEL_MAPPING_V1 — dataset-semantic gold labels.

Gold UNCERTAIN describes semantic uncertainty in the input evidence.
Inference-time UNCERTAIN describes the model's decision state.
Inference uncertainty MUST NOT create or modify gold UNCERTAIN examples.
"""

from __future__ import annotations

from typing import Any, Mapping

RULE_ID = "HYPERLEX_V5_STAGE_A_GOLD_LABEL_MAPPING_V1"
SCHEMA = "hyperlex.classification.v5.stage_a_gold_label_mapping.v1"

GOLD_LABELS = ("NO_EVIDENCE", "EVIDENCE_PRESENT", "UNCERTAIN")
GOLD_LABEL_INDEX = {
    "NO_EVIDENCE": 0,
    "EVIDENCE_PRESENT": 1,
    "UNCERTAIN": 2,
}

POSITIVE_SUBTYPE = "POSITIVE_EVIDENCE"
NONE_SUBTYPES = frozenset(
    {
        "ORDINARY_DOMAIN_NONE",
        "HARD_NONE",
        "NEAR_DOMAIN_NONE",
        "GENERIC_NONE",
        "LEXICAL_LOOKALIKE_NONE",
        "SHORT_ATOM_NONE",
    }
)
UNCERTAIN_SUBTYPE = "AMBIGUOUS_EVIDENCE"

SUBTYPE_TO_GOLD: dict[str, str] = {
    "POSITIVE_EVIDENCE": "EVIDENCE_PRESENT",
    "ORDINARY_DOMAIN_NONE": "NO_EVIDENCE",
    "HARD_NONE": "NO_EVIDENCE",
    "NEAR_DOMAIN_NONE": "NO_EVIDENCE",
    "GENERIC_NONE": "NO_EVIDENCE",
    "LEXICAL_LOOKALIKE_NONE": "NO_EVIDENCE",
    "SHORT_ATOM_NONE": "NO_EVIDENCE",
    "AMBIGUOUS_EVIDENCE": "UNCERTAIN",
}

ALLOWED_AMBIGUITY_REASONS = frozenset(
    {
        "INSUFFICIENT_CONTEXT",
        "CONFLICTING_EVIDENCE",
        "PARTIAL_REQUIRED_CORE",
        "MULTIPLE_PLAUSIBLE_INTERPRETATIONS",
        "UNRESOLVED_SOURCE_MEANING",
    }
)

FORBIDDEN_GOLD_DERIVATION_SOURCES = frozenset(
    {
        "model_probability",
        "threshold_outcome",
        "retrieval_score",
        "nearest_neighbor_score",
        "prototype_score",
        "reserve_behavior",
        "jev",
    }
)

LABEL_MAPPING_INVALID = "LABEL_MAPPING_INVALID"


class LabelMappingError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}:{detail}" if detail else code)


def _normalize_required(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    text = str(value).strip().lower()
    if text in {"true", "false", "uncertain"}:
        return text
    raise LabelMappingError(LABEL_MAPPING_INVALID, f"required_evidence_present:{value!r}")


def _ambiguity_reason_present(row: Mapping[str, Any]) -> bool:
    notes = row.get("notes")
    if isinstance(notes, Mapping):
        reason = notes.get("ambiguity_reason") or notes.get("uncertain_reason")
        if reason in ALLOWED_AMBIGUITY_REASONS:
            return True
    for key in ("ambiguity_reason", "uncertain_reason"):
        if row.get(key) in ALLOWED_AMBIGUITY_REASONS:
            return True
    for item in row.get("missing_required_semantics") or []:
        if isinstance(item, Mapping):
            reason = item.get("ambiguity_reason") or item.get("reason")
            if reason in ALLOWED_AMBIGUITY_REASONS:
                return True
        elif item in ALLOWED_AMBIGUITY_REASONS:
            return True
    for span_key in ("evidence_spans", "positive_evidence_spans", "negative_evidence_spans"):
        for item in row.get(span_key) or []:
            if isinstance(item, Mapping) and item.get("ambiguity_reason") in ALLOWED_AMBIGUITY_REASONS:
                return True
    # Surface contract: AMBIGUOUS_EVIDENCE subtype itself encodes unresolved
    # evidence sufficiency; require at least one non-empty semantic marker.
    if row.get("evidence_subtype") == UNCERTAIN_SUBTYPE:
        markers = (
            row.get("missing_required_semantics")
            or row.get("candidate_families")
            or row.get("shared_cues")
            or row.get("notes")
        )
        return bool(markers)
    return False


def gold_label(row: Mapping[str, Any]) -> str:
    """Deterministic subtype→gold mapping. Fail closed on any mismatch."""
    subtype = str(row.get("evidence_subtype") or "")
    required = _normalize_required(row.get("required_evidence_present"))

    if subtype == POSITIVE_SUBTYPE:
        if required != "true":
            raise LabelMappingError(LABEL_MAPPING_INVALID, "positive_requires_required_true")
        support = row.get("active_family_support") or []
        if not support:
            raise LabelMappingError(LABEL_MAPPING_INVALID, "positive_without_family_support")
        basis = row.get("positive_evidence_spans") or row.get("evidence_spans") or []
        if not basis:
            raise LabelMappingError(LABEL_MAPPING_INVALID, "positive_evidence_basis_empty")
        return "EVIDENCE_PRESENT"

    if subtype in NONE_SUBTYPES:
        if required != "false":
            raise LabelMappingError(LABEL_MAPPING_INVALID, "none_requires_required_false")
        return "NO_EVIDENCE"

    if subtype == UNCERTAIN_SUBTYPE:
        if required != "uncertain":
            raise LabelMappingError(LABEL_MAPPING_INVALID, "uncertain_requires_required_uncertain")
        if not _ambiguity_reason_present(row):
            raise LabelMappingError(LABEL_MAPPING_INVALID, "uncertain_without_reason")
        return "UNCERTAIN"

    raise LabelMappingError(LABEL_MAPPING_INVALID, f"unknown_subtype:{subtype}")


def validate_row_gold_mapping(row: Mapping[str, Any]) -> list[str]:
    """Return invariant violation codes; empty list means admitable."""
    errors: list[str] = []
    subtype = str(row.get("evidence_subtype") or "")
    if subtype not in SUBTYPE_TO_GOLD:
        errors.append("unknown_subtype")
        return errors
    try:
        mapped = gold_label(row)
    except LabelMappingError as exc:
        if "positive_without_family_support" in str(exc):
            errors.append("positive_without_family_support")
        elif "uncertain_without_reason" in str(exc):
            errors.append("uncertain_without_reason")
        elif "required_true" in str(exc) or "required_false" in str(exc) or "required_uncertain" in str(exc):
            errors.append("required_evidence_gold_mismatch")
        else:
            errors.append(LABEL_MAPPING_INVALID)
        return errors

    declared = str(row.get("evidence_label") or "")
    if declared and declared != mapped:
        errors.append("subtype_gold_mismatch")
    expected = SUBTYPE_TO_GOLD[subtype]
    if mapped != expected:
        errors.append("subtype_gold_mismatch")
    return errors


def admission_invariants(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    counts = {
        "subtype_gold_mismatch": 0,
        "required_evidence_gold_mismatch": 0,
        "positive_without_family_support": 0,
        "uncertain_without_reason": 0,
        "unknown_subtype": 0,
        "LABEL_MAPPING_INVALID": 0,
        "n_rows": len(rows),
        "n_invalid": 0,
    }
    invalid_identities: list[str] = []
    for row in rows:
        errs = validate_row_gold_mapping(row)
        if not errs:
            continue
        counts["n_invalid"] += 1
        invalid_identities.append(str(row.get("identity") or ""))
        for err in errs:
            counts[err] = int(counts.get(err) or 0) + 1
    counts["pass"] = counts["n_invalid"] == 0
    counts["rule"] = RULE_ID
    counts["schema"] = SCHEMA
    counts["invalid_identities_sample"] = [i for i in invalid_identities if i][:20]
    return counts


def mapping_contract() -> dict[str, Any]:
    return {
        "CRITICAL_INVARIANT": (
            "Gold UNCERTAIN describes semantic uncertainty in the input evidence. "
            "Inference-time UNCERTAIN describes the model's decision state. "
            "They may share the output label, but inference uncertainty MUST NOT "
            "be used retroactively to create or modify gold UNCERTAIN examples."
        ),
        "FORBIDDEN_GOLD_DERIVATION_SOURCES": sorted(FORBIDDEN_GOLD_DERIVATION_SOURCES),
        "GOLD_LABEL_INDEX": dict(GOLD_LABEL_INDEX),
        "GOLD_LABELS": list(GOLD_LABELS),
        "RULE_ID": RULE_ID,
        "SCHEMA": SCHEMA,
        "STAGE_C_AMBIGUOUS_DISTINCT": (
            "If evidence is clearly present but supports multiple families, "
            "Stage-A gold = EVIDENCE_PRESENT; family ambiguity is Stage-C AMBIGUOUS."
        ),
        "SUBTYPE_TO_GOLD": dict(SUBTYPE_TO_GOLD),
        "ALLOWED_AMBIGUITY_REASONS": sorted(ALLOWED_AMBIGUITY_REASONS),
    }
