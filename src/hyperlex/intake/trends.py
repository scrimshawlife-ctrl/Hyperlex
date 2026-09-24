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


import os
from importlib.util import find_spec

from .cache import cache_key, get_cached, rate_window_open, set_cached, stamp_rate_limit
from .sources import offline_mode


def trends_geo_timeframe() -> tuple[str, str]:
    geo = os.environ.get("HYPERLEX_TRENDS_GEO", "")
    geo = geo.strip() if isinstance(geo, str) else ""
    timeframe = os.environ.get("HYPERLEX_TRENDS_TIMEFRAME", "").strip() or DEFAULT_TIMEFRAME
    return geo, timeframe


def pytrends_import_status() -> str:
    if find_spec("pytrends") is None:
        return "missing"
    try:
        from pytrends.request import TrendReq  # noqa: F401
    except ModuleNotFoundError:
        return "missing"
    return "ok"


def _is_offline(flag: Optional[bool]) -> bool:
    if flag is True or offline_mode():
        return True
    return False


def _is_rate_limited(exc: BaseException) -> bool:
    response = getattr(exc, "response", None)
    if getattr(response, "status_code", None) == 429:
        return True
    return "code 429" in str(exc)


def _trends_cache_key(query: str, geo: str, timeframe: str) -> str:
    return cache_key(f"{query}|{geo}|{timeframe}", "trends")


def _read_cache(query: str, geo: str, timeframe: str) -> Optional[Dict[str, Any]]:
    raw = get_cached(_trends_cache_key(query, geo, timeframe), source="trends")
    if not isinstance(raw, str):
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _write_cache(packet: Dict[str, Any], query: str, geo: str, timeframe: str) -> None:
    set_cached(
        _trends_cache_key(query, geo, timeframe),
        json.dumps(packet, sort_keys=True),
        source="trends",
    )


def _put(ingest: Dict[str, Any], packet: Dict[str, Any]) -> Dict[str, Any]:
    ingest["trends"] = packet
    return ingest


def attach_trends(
    ingest: Dict[str, Any],
    *,
    route: Optional[str],
    offline: Optional[bool] = None,
    client: Optional[Any] = None,
) -> Dict[str, Any]:
    route_name = (route or "").strip().lower()
    if route_name not in {"trends", "live"}:
        return ingest
    try:
        return _attach_trends(ingest, route_name=route_name, offline=offline, client=client)
    except Exception as exc:
        if route_name == "live" and _is_offline(offline):
            return ingest
        geo, timeframe = trends_geo_timeframe()
        query = str(ingest.get("query") or "").strip()
        reason = "rate_limited" if _is_rate_limited(exc) else "fetch_failed"
        error_class = None if reason == "rate_limited" else type(exc).__name__
        return _put(
            ingest,
            build_trends_packet(
                query=query,
                geo=geo,
                timeframe=timeframe,
                failure=reason,
                error_class=error_class,
            ),
        )


def _attach_trends(
    ingest: Dict[str, Any],
    *,
    route_name: str,
    offline: Optional[bool],
    client: Optional[Any],
) -> Dict[str, Any]:
    if _is_offline(offline):
        if route_name == "live":
            return ingest
        geo, timeframe = trends_geo_timeframe()
        return _put(
            ingest,
            build_trends_packet(
                query=str(ingest.get("query") or "").strip(),
                geo=geo,
                timeframe=timeframe,
                failure="offline",
            ),
        )

    if client is None:
        try:
            status = pytrends_import_status()
        except Exception as exc:
            geo, timeframe = trends_geo_timeframe()
            return _put(
                ingest,
                build_trends_packet(
                    query=str(ingest.get("query") or "").strip(),
                    geo=geo,
                    timeframe=timeframe,
                    failure="fetch_failed",
                    error_class=type(exc).__name__,
                ),
            )
        if status == "missing":
            if route_name == "live":
                return ingest
            geo, timeframe = trends_geo_timeframe()
            return _put(
                ingest,
                build_trends_packet(
                    query=str(ingest.get("query") or "").strip(),
                    geo=geo,
                    timeframe=timeframe,
                    failure="trends_extra_missing",
                ),
            )
        client = PytrendsClient()

    geo, timeframe = trends_geo_timeframe()
    query = str(ingest.get("query") or "").strip()
    if not query or len(query) > 100:
        return _put(
            ingest,
            build_trends_packet(query=query, geo=geo, timeframe=timeframe, failure="query_rejected"),
        )

    cached = _read_cache(query, geo, timeframe)
    if cached is not None:
        copied = dict(cached)
        copied["cached"] = True
        return _put(ingest, copied)

    if not rate_window_open("trends"):
        return _put(
            ingest,
            build_trends_packet(query=query, geo=geo, timeframe=timeframe, failure="rate_limited"),
        )

    try:
        raw = client.fetch(query, geo=geo, timeframe=timeframe)
    except Exception as exc:
        stamp_rate_limit("trends")
        reason = "rate_limited" if _is_rate_limited(exc) else "fetch_failed"
        return _put(
            ingest,
            build_trends_packet(
                query=query,
                geo=geo,
                timeframe=timeframe,
                failure=reason,
                error_class=None if reason == "rate_limited" else type(exc).__name__,
            ),
        )
    stamp_rate_limit("trends")
    payload = raw if isinstance(raw, dict) else {}
    packet = build_trends_packet(
        query=query,
        geo=geo,
        timeframe=timeframe,
        interest_over_time=payload.get("interest_over_time") or [],
        related_queries=payload.get("related_queries") or {},
    )
    if packet["status"] in {"ok", "empty"}:
        _write_cache(packet, query, geo, timeframe)
    return _put(ingest, packet)


def _new_trend_req():
    from pytrends.request import TrendReq

    return TrendReq(hl="en-US", tz=0, timeout=(5, 20), retries=2, backoff_factor=0.3)


def _interest_from_frame(frame: Any, query: str) -> List[Dict[str, Any]]:
    if frame is None or getattr(frame, "empty", True):
        return []
    columns = list(getattr(frame, "columns", []))
    value_col = query if query in columns else next((col for col in columns if col != "isPartial"), None)
    rows: List[Dict[str, Any]] = []
    for idx, row in frame.iterrows():
        date = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
        value = row.get(value_col) if value_col is not None else None
        partial = bool(row.get("isPartial", False))
        rows.append({"date": date, "value": value, "partial": partial})
    return rows


def _related_from_payload(payload: Any, query: str) -> Dict[str, List[Dict[str, Any]]]:
    block: Any = {}
    if isinstance(payload, dict):
        block = payload.get(query) or {}
        if not block and len(payload) == 1:
            block = next(iter(payload.values()))
    if not isinstance(block, dict):
        block = {}

    def rows(frame: Any) -> List[Dict[str, Any]]:
        if frame is None or getattr(frame, "empty", True):
            return []
        out: List[Dict[str, Any]] = []
        for _, row in frame.iterrows():
            out.append({"query": row.get("query"), "value": row.get("value")})
        return out

    return {"top": rows(block.get("top")), "rising": rows(block.get("rising"))}


class PytrendsClient:
    def fetch(self, query: str, *, geo: str, timeframe: str) -> Dict[str, Any]:
        req = _new_trend_req()
        req.build_payload([query], timeframe=timeframe, geo=geo)
        interest = _interest_from_frame(req.interest_over_time(), query)
        related = _related_from_payload(req.related_queries(), query)
        return {"interest_over_time": interest, "related_queries": related}
