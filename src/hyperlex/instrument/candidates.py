"""Advisory candidate + neighborhood generation (never hard labels)."""

from __future__ import annotations

import re
from typing import Any

from .constants import (
    CANDIDATE_SCORE_FLOOR,
    DOMAIN_CONCEPTS,
    FUNCTION_CONCEPTS,
    MEDIATION_CONCEPTS,
    NEIGHBORHOOD_TOP_K,
    RESEARCH_ONLY_CONCEPTS,
)

_TOKEN = re.compile(r"[a-z0-9']{2,}")


def _score_concept(text: str, cues: tuple[str, ...]) -> float:
    tl = (text or "").lower()
    if not tl.strip():
        return 0.0
    hits = sum(1 for c in cues if c in tl)
    if hits == 0:
        return 0.0
    return min(1.0, hits / max(3.0, len(cues) * 0.25))


def build_candidates(
    text: str,
    *,
    include_function: bool = True,
) -> list[dict[str, Any]]:
    """Emit advisory candidates only. memetic_form never emitted."""
    out: list[dict[str, Any]] = []
    for concept_id, cues in DOMAIN_CONCEPTS.items():
        s = _score_concept(text, cues)
        if s >= CANDIDATE_SCORE_FLOOR:
            out.append(
                {
                    "concept_id": concept_id,
                    "score": round(s, 6),
                    "axis": "domain",
                    "advisory": True,
                    "status": "advisory",
                }
            )
    for concept_id, cues in MEDIATION_CONCEPTS.items():
        s = _score_concept(text, cues)
        if s >= CANDIDATE_SCORE_FLOOR:
            out.append(
                {
                    "concept_id": concept_id,
                    "score": round(s, 6),
                    "axis": "mediation",
                    "advisory": True,
                    "status": "advisory",
                }
            )
    if include_function:
        for concept_id, cues in FUNCTION_CONCEPTS.items():
            if concept_id in RESEARCH_ONLY_CONCEPTS:
                continue
            s = _score_concept(text, cues)
            if s >= CANDIDATE_SCORE_FLOOR:
                out.append(
                    {
                        "concept_id": concept_id,
                        "score": round(s, 6),
                        "axis": "function",
                        "advisory": True,
                        "status": "experimental_or_advisory",
                    }
                )
    out.sort(key=lambda r: (-float(r["score"]), r["concept_id"]))
    assert all(c.get("advisory") is True for c in out)
    assert not any(c["concept_id"] in RESEARCH_ONLY_CONCEPTS for c in out)
    return out


def build_neighborhood(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Neighborhood from candidate scores (similarity proxy)."""
    neigh = [
        {"concept_id": c["concept_id"], "similarity": float(c["score"])}
        for c in candidates
    ]
    neigh.sort(key=lambda r: (-r["similarity"], r["concept_id"]))
    return neigh[:NEIGHBORHOOD_TOP_K]
