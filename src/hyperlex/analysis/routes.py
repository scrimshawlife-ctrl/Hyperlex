"""Dual-route labels for open analysis.

``form`` and ``lexical`` only. Never ``semantic`` on an unsettle unit.
Not Brier. Not IsA.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

SCHEMA = "hyperlex.route_labels.v0.1"
ALLOWED = frozenset({"form", "lexical"})
LINEAGE_THRESHOLD = 0.42
FORBIDDEN_KEYS = frozenset(
    {"meaning", "has_meaning", "comprehension", "isa_grade", "semantic"}
)


class RouteLabelError(ValueError):
    """Fail-closed packet."""


def _conf(block: Mapping[str, Any] | None) -> float:
    if not block:
        return 0.0
    br = block.get("score_breakdown") or {}
    for key in ("hybrid_confidence", "lexical_confidence", "confidence"):
        if key in br:
            try:
                return float(br[key])
            except (TypeError, ValueError):
                continue
        if key in block:
            try:
                return float(block[key])
            except (TypeError, ValueError):
                continue
    return 0.0


def _lexical_licensed(analysis: Mapping[str, Any]) -> bool:
    lin = analysis.get("lineage")
    if not isinstance(lin, Mapping):
        return False
    if lin.get("family_id") and _conf(lin) >= LINEAGE_THRESHOLD:
        return True
    return _conf(lin) >= LINEAGE_THRESHOLD


def _form_licensed(analysis: Mapping[str, Any], lexical: bool) -> bool:
    neos = analysis.get("neologisms") or []
    if isinstance(neos, list):
        for n in neos:
            if isinstance(n, Mapping) and n.get("formation"):
                return True
    trace = analysis.get("mutation_trace")
    if isinstance(trace, Mapping):
        ops = trace.get("operators") or trace.get("layers") or trace.get("tags")
        if ops:
            return True
    watch = analysis.get("mutation_watch")
    if isinstance(watch, Mapping) and (
        watch.get("operators") or watch.get("score") is not None
    ):
        return True
    if not lexical and isinstance(analysis.get("vector_neighbors"), Mapping):
        hits = analysis["vector_neighbors"].get("hits") or []
        if hits:
            return True
    return False


def label_routes(analysis: Mapping[str, Any] | None) -> Dict[str, Any]:
    """Build a valid route-label block from an analysis dict."""
    src = analysis or {}
    lexical = _lexical_licensed(src)
    form = _form_licensed(src, lexical)
    fired: List[str] = []
    if form:
        fired.append("form")
    if lexical:
        fired.append("lexical")
    block = {
        "schema": SCHEMA,
        "routes_fired": fired,
        "semantic_claimed": False,
        "brier": None,
    }
    return validate_route_block(block)


def validate_route_block(block: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(block, Mapping):
        raise RouteLabelError("route block must be an object")
    for k in FORBIDDEN_KEYS:
        if k in block:
            raise RouteLabelError(f"forbidden key {k!r}")
    if block.get("schema") != SCHEMA:
        raise RouteLabelError("schema mismatch")
    if block.get("semantic_claimed") is not False:
        raise RouteLabelError("semantic_claimed must be false")
    if block.get("brier") is not None:
        raise RouteLabelError("brier must be null")
    fired = block.get("routes_fired")
    if not isinstance(fired, list):
        raise RouteLabelError("routes_fired must be a list")
    seen = []
    for tok in fired:
        if tok not in ALLOWED:
            raise RouteLabelError(f"illegal route token {tok!r}")
        if tok not in seen:
            seen.append(tok)
    out: Dict[str, Any] = {
        "schema": SCHEMA,
        "routes_fired": seen,
        "semantic_claimed": False,
        "brier": None,
    }
    notes = block.get("notes")
    if notes is not None:
        if not isinstance(notes, list) or any(not isinstance(n, str) for n in notes):
            raise RouteLabelError("notes must be a list of strings")
        out["notes"] = list(notes)
    return out


def attach_route_labels(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Mutate analysis in place; return the block."""
    block = label_routes(analysis)
    analysis["routes"] = block
    return block


def render_route_line(block: Mapping[str, Any] | None) -> str:
    b = validate_route_block(block or label_routes({}))
    fired = ", ".join(b["routes_fired"]) or "(none)"
    return f"Routes: {fired}. Semantic: no. Brier: null."
