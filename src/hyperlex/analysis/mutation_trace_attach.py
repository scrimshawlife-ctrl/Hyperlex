"""Fail-open attach of mutation_trace onto an analysis dict."""
from __future__ import annotations

from typing import Any, Dict, Optional


def attach_mutation_trace(
    analysis: Dict[str, Any],
    *,
    query: str = "",
    observed: str = "",
    ingest_source: Optional[str] = None,
) -> None:
    try:
        from ..mutation import parse_mutation_trace

        span = " ".join(x for x in [query, observed] if x).strip() or str(query or "")
        mt = parse_mutation_trace(str(span), source=str(ingest_source or "analyze"))
        if mt.get("operators"):
            analysis["mutation_trace"] = mt
    except Exception:
        return
