"""Diagnostics with honest unavailable states."""

from __future__ import annotations

from typing import Any, Sequence


def build_diagnostics(candidates: Sequence[dict[str, Any]]) -> dict[str, Any]:
    unavailable = ["distribution_distance", "representation_drift"]
    if not candidates:
        return {
            "margin": None,
            "ambiguity": None,
            "distribution_distance": None,
            "representation_drift": None,
            "unavailable": unavailable + ["margin", "ambiguity"],
        }
    scores = sorted((float(c["score"]) for c in candidates), reverse=True)
    top = scores[0]
    second = scores[1] if len(scores) > 1 else 0.0
    margin = round(top - second, 6)
    # Ambiguity: how close the mass is among top scores (0=sharp, 1=flat).
    if len(scores) == 1:
        ambiguity = 0.0
    else:
        spread = sum(abs(top - s) for s in scores[:5]) / (5.0 * max(top, 1e-9))
        ambiguity = round(max(0.0, min(1.0, 1.0 - spread)), 6)
    return {
        "margin": margin,
        "ambiguity": ambiguity,
        "distribution_distance": None,
        "representation_drift": None,
        "unavailable": list(unavailable),
    }
