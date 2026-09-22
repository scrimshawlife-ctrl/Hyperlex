"""Observed Google Trends evidence. pytrends is imported only by the live client."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from ..provenance import source_fingerprint

SCHEMA = "hyperlex.trends_evidence.v1"
DEFAULT_TIMEFRAME = "today 3-m"
RELATED_CAP = 25
SCALE_NOTE = (
    "Peak in this window is 100. Values are not probabilities and are not "
    "comparable across separate fetches."
)
PACKET_KEYS = (
    "schema",
    "status",
    "reason",
    "query",
    "geo",
    "timeframe",
    "cached",
    "fetched_at",
    "interest_over_time",
    "related_queries",
    "dropped_rows",
    "truncated",
    "scale",
    "claims",
    "brier",
    "error_class",
    "source_fingerprint",
)


def _whole_int(value: Any) -> Optional[int]:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return None
    if isinstance(value, int):
        return value
    is_integer = getattr(value, "is_integer", None)
    if callable(is_integer):
        try:
            if not is_integer():
                return None
            return int(value)
        except (TypeError, ValueError):
            return None
    if isinstance(value, float):
        if math.isnan(value) or not value.is_integer():
            return None
        return int(value)
    try:
        as_int = int(value)
    except (TypeError, ValueError):
        return None
    return as_int


def _normalize_interest(rows: List[Any]) -> tuple[List[Dict[str, Any]], int]:
    kept: List[Dict[str, Any]] = []
    dropped = 0
    for row in rows or []:
        if not isinstance(row, dict):
            dropped += 1
            continue
        number = _whole_int(row.get("value"))
        date = row.get("date")
        date_s = str(date)[:10] if isinstance(date, str) and len(str(date)) >= 10 else ""
        if number is None or not 0 <= number <= 100 or len(date_s) != 10:
            dropped += 1
            continue
        kept.append({"date": date_s, "value": number, "partial": bool(row.get("partial", False))})
    return kept, dropped


def _normalize_related(payload: Optional[Dict[str, Any]]) -> tuple[Dict[str, List[Dict[str, Any]]], bool]:
    raw = payload or {}
    out: Dict[str, List[Dict[str, Any]]] = {"top": [], "rising": []}
    truncated = False
    for key in ("top", "rising"):
        rows = raw.get(key) or []
        if not isinstance(rows, list):
            rows = []
        cleaned: List[Dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            text = row.get("query")
            if not isinstance(text, str) or not text.strip():
                continue
            value = row.get("value")
            if isinstance(value, str):
                stored: Any = value
            else:
                stored = _whole_int(value)
                if stored is None:
                    continue
            cleaned.append({"query": text, "value": stored})
        if len(cleaned) > RELATED_CAP:
            truncated = True
            cleaned = cleaned[:RELATED_CAP]
        out[key] = cleaned
    return out, truncated


def _claims(label: str) -> List[Dict[str, str]]:
    return [
        {"statement": "interest_over_time", "label": label},
        {"statement": "related_queries", "label": label},
    ]


def _with_fingerprint(body: Dict[str, Any], *, query: str, geo: str, timeframe: str, fetched_at: str) -> Dict[str, Any]:
    locator = f"hyperlex://trends?geo={quote(geo, safe='')}&timeframe={quote(timeframe, safe='')}"
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    body["source_fingerprint"] = source_fingerprint(
        source="trends",
        query=query,
        raw_signal=raw,
        source_locator=locator,
        fetched_at=fetched_at,
    )
    return body


def build_trends_packet(
    *,
    query: str,
    geo: str,
    timeframe: str,
    interest_over_time: Optional[list] = None,
    related_queries: Optional[dict] = None,
    failure: Optional[str] = None,
    error_class: Optional[str] = None,
    cached: bool = False,
    fetched_at: Optional[str] = None,
) -> Dict[str, Any]:
    fetched = fetched_at or datetime.now(timezone.utc).isoformat()
    if failure:
        body: Dict[str, Any] = {
            "schema": SCHEMA,
            "status": "not_computable",
            "reason": failure,
            "query": query,
            "geo": geo,
            "timeframe": timeframe,
            "cached": cached,
            "fetched_at": fetched,
            "interest_over_time": [],
            "related_queries": {"top": [], "rising": []},
            "dropped_rows": 0,
            "truncated": False,
            "scale": {"interest": "relative_0_100_within_this_request", "note": SCALE_NOTE},
            "claims": _claims("NOT_COMPUTABLE"),
            "brier": None,
            "error_class": error_class if failure == "fetch_failed" else None,
        }
        return _with_fingerprint(body, query=query, geo=geo, timeframe=timeframe, fetched_at=fetched)

    interest, dropped = _normalize_interest(list(interest_over_time or []))
    related, truncated = _normalize_related(related_queries)
    has_rows = bool(interest or related["top"] or related["rising"])
    body = {
        "schema": SCHEMA,
        "status": "ok" if has_rows else "empty",
        "reason": None if has_rows else "below_trends_threshold",
        "query": query,
        "geo": geo,
        "timeframe": timeframe,
        "cached": cached,
        "fetched_at": fetched,
        "interest_over_time": interest,
        "related_queries": related,
        "dropped_rows": dropped,
        "truncated": truncated,
        "scale": {"interest": "relative_0_100_within_this_request", "note": SCALE_NOTE},
        "claims": _claims("OBSERVED"),
        "brier": None,
        "error_class": None,
    }
    return _with_fingerprint(body, query=query, geo=geo, timeframe=timeframe, fetched_at=fetched)
