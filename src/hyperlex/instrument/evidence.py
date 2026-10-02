"""Evidence / NONE / abstention signal for Hyperlex Instrument V1."""

from __future__ import annotations

import re
from typing import Any

from .constants import (
    DOMAIN_CONCEPTS,
    FUNCTION_CONCEPTS,
    MEDIATION_CONCEPTS,
)

_TOKEN = re.compile(r"[a-z0-9']{2,}")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN.findall((text or "").lower()))


def _cue_hit_count(text: str) -> int:
    tl = (text or "").lower()
    hits = 0
    for cues in (
        *DOMAIN_CONCEPTS.values(),
        *MEDIATION_CONCEPTS.values(),
        *FUNCTION_CONCEPTS.values(),
    ):
        for c in cues:
            if c in tl:
                hits += 1
    return hits


def build_evidence(text: str) -> dict[str, Any]:
    """First-class abstention: empty / cue-less text → present=false, abstain=true."""
    toks = _tokens(text)
    if not toks:
        return {
            "present": False,
            "score": 0.0,
            "abstain": True,
            "reason": "no_content_tokens",
        }
    hits = _cue_hit_count(text)
    # Soft score from cue density; does not force candidates.
    score = min(1.0, hits / 6.0) if hits else 0.05
    # Abstain when no ontology cue support — valid empty-candidate outcome.
    if hits == 0:
        return {
            "present": False,
            "score": round(score, 6),
            "abstain": True,
            "reason": "no_ontology_cue_support",
        }
    return {
        "present": True,
        "score": round(score, 6),
        "abstain": False,
        "reason": None,
    }
