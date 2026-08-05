"""Epistemic claim labels (Abraxas / Hyperlex shared discipline).

Wire values only — no Abraxas import.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

CLAIM_LABELS = ("OBSERVED", "INFERRED", "SPECULATIVE", "NOT_COMPUTABLE")
NOT_COMPUTABLE = "NOT_COMPUTABLE"


def label_claim(
    statement: str,
    label: str,
    *,
    evidence_ref: Optional[str] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a single labeled claim dict."""
    lab = str(label).upper()
    if lab not in CLAIM_LABELS:
        raise ValueError(f"label must be one of {CLAIM_LABELS}")
    out: Dict[str, Any] = {"statement": statement, "label": lab}
    if evidence_ref is not None:
        out["evidence_ref"] = evidence_ref
    if note is not None:
        out["note"] = note
    return out
