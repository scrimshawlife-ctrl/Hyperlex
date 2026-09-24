# Pytrends Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Attach an observed Google Trends packet for the operator's term on `--route trends` and, when pytrends imports and the process is online, on `--route live`.

**Architecture:** `intake/trends.py` is the only module that imports pytrends. It maps responses to a plain dict and caches that dict through the existing disk cache. `fetch_ingest` calls `attach_trends` after the language fingerprint is built. `detect_memetic_patterns` copies the packet to top-level `result["trends"]`. Language text stays on `combined` (or `mock` when offline). Virality, Brier, and `analysis_canonical_hash` do not read the packet.

**Tech Stack:** Python 3.10+, existing `hyperlex.intake.cache` and `hyperlex.provenance.source_fingerprint`, optional extra `pytrends>=4.9` (pulls pandas; tests never import it).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-22-pytrends-evidence-design.md`. This plan implements that spec only.
- Schema name: `hyperlex.trends_evidence.v1`.
- `brier` on every Trends packet is `null`. `provenance.brier` on the analysis result stays `null`.
- Interest `value` is an int from 0 through 100 inclusive. A whole-number float or numpy integer is stored as a Python int. A non-whole number or NaN is dropped and counted in `dropped_rows`.
- A numeric related-query value is stored as an int. A string value is stored as a string, including `Breakout`.
- Each related list keeps at most 25 rows. `truncated` is true when either list was longer.
- Default timeframe is `today 3-m`. Default geo is `""` (worldwide). Whitespace-only geo is `""`.
- `SOURCE_TTL["trends"]` is `21600`. `SOURCE_MIN_INTERVAL["trends"]` is `60.0`.
- Cache status `ok` and `empty` only. A cache hit returns a copy with `cached: true` and does not rewrite the file or stamp the rate file.
- Stamp `trends` in the rate file on every network attempt, including a failed one. Do not stamp on cache hits, offline, a missing extra, query rejection, or a closed window.
- `rate_window_open` and `stamp_rate_limit` do not sleep. `wait_for_rate_limit` stays unused by Trends.
- pytrends is imported only inside the live client, not at module import. The default suite does not call Google.
- A query of exactly 100 characters is allowed. 101 characters, or empty after strip, is `query_rejected`.
- `--route trends` always has a `trends` key. `--route live` omits the key when offline or when pytrends is missing. Other routes omit the key.
- The extra check runs only when no client is injected. An injected client is the test seam and skips the import.
- Do not modify `src/hyperlex/receipt/__init__.py`, virality math, settlement, the package version, or the default offline route used by demo, wizard, and `run`.
- Do not edit `CHANGELOG.md`, `docs/commands.md`, or `docs/hermes-skill.md`.
- Run tests as `PYTHONPATH=src python -m pytest …` from the repo root `/Users/appliedalchemylabs/Hyperlex`.

---

### Task 1: Trends cache TTL and non-blocking rate window

**Files:**
- Modify: `src/hyperlex/intake/cache.py` (the `SOURCE_TTL` and `SOURCE_MIN_INTERVAL` dicts, and two functions inserted immediately above `def wait_for_rate_limit`)
- Test: `tests/test_trends_evidence.py`

**Interfaces:**
- Consumes: existing `min_interval_for`, `_load_rate_state`, `_save_rate_state`, `ttl_for`.
- Produces:
  - `SOURCE_TTL["trends"] == 21600`
  - `SOURCE_MIN_INTERVAL["trends"] == 60.0`
  - `rate_window_open(source: str) -> bool`
  - `stamp_rate_limit(source: str) -> None`
  - pytest fixture `trends_env(tmp_path, monkeypatch) -> Path` in the new test module.

- [ ] **Step 1: Write the failing test**

Create `tests/test_trends_evidence.py`:

```python
"""Google Trends evidence packet. No network. No pytrends import."""

from __future__ import annotations

import time

import pytest


@pytest.fixture
def trends_env(tmp_path, monkeypatch):
    monkeypatch.setenv("HYPERLEX_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("HYPERLEX_RATE_LIMIT_PATH", str(tmp_path / "rate_limit.json"))
    for name in (
        "HYPERLEX_OFFLINE",
        "HYPERLEX_NO_RATE_LIMIT",
        "HYPERLEX_TRENDS_GEO",
        "HYPERLEX_TRENDS_TIMEFRAME",
        "HYPERLEX_SOURCE_MIN_INTERVAL_TRENDS",
    ):
        monkeypatch.delenv(name, raising=False)
    return tmp_path


def test_trends_ttl_and_interval(trends_env):
    from hyperlex.intake.cache import (
        SOURCE_MIN_INTERVAL,
        min_interval_for,
        ttl_for,
    )

    assert ttl_for("trends") == 21600
    assert min_interval_for("trends") == 60.0
    assert SOURCE_MIN_INTERVAL["trends"] == 60.0


def test_trends_interval_env_override(trends_env, monkeypatch):
    from hyperlex.intake.cache import min_interval_for

    monkeypatch.setenv("HYPERLEX_SOURCE_MIN_INTERVAL_TRENDS", "5")
    assert min_interval_for("trends") == 5.0


def test_rate_window_does_not_sleep_and_closes_after_stamp(trends_env, monkeypatch):
    from hyperlex.intake.cache import rate_window_open, stamp_rate_limit

    def _boom(*_a, **_k):
        raise AssertionError("trends rate helpers must not sleep")

    monkeypatch.setattr(time, "sleep", _boom)
    assert rate_window_open("trends") is True
    stamp_rate_limit("trends")
    assert rate_window_open("trends") is False


def test_no_rate_limit_env_keeps_window_open(trends_env, monkeypatch):
    from hyperlex.intake.cache import rate_window_open, stamp_rate_limit

    stamp_rate_limit("trends")
    monkeypatch.setenv("HYPERLEX_NO_RATE_LIMIT", "1")
    assert rate_window_open("trends") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_trends_evidence.py -v`

Expected: FAIL. `ttl_for("trends")` is 300 (the default), and `rate_window_open` is not defined.

- [ ] **Step 3: Write minimal implementation**

In `src/hyperlex/intake/cache.py`, add to `SOURCE_TTL`:

```python
    "trends": 21600,
```

Add to `SOURCE_MIN_INTERVAL`:

```python
    "trends": 60.0,
```

Insert immediately above `def wait_for_rate_limit`:

```python
def rate_window_open(source: str) -> bool:
    """True when a live fetch for ``source`` is allowed now.

    Does not sleep and does not stamp. ``HYPERLEX_NO_RATE_LIMIT=1`` is open.
    A minimum interval of 0 is open.
    """
    flag = str(os.environ.get("HYPERLEX_NO_RATE_LIMIT", "")).strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        return True
    src = (source or "").strip().lower()
    min_iv = float(min_interval_for(src))
    if min_iv <= 0:
        return True
    last = float(_load_rate_state().get(src, 0.0))
    return (time.time() - last) >= min_iv


def stamp_rate_limit(source: str) -> None:
    """Record now as the last attempt for ``source``. Does not sleep."""
    src = (source or "").strip().lower()
    state = _load_rate_state()
    state[src] = time.time()
    _save_rate_state(state)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_trends_evidence.py -v`

Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/hyperlex/intake/cache.py tests/test_trends_evidence.py
git commit -m "feat: add non-blocking trends rate window"
```

---

### Task 2: `--route trends` preset

**Files:**
- Modify: `src/hyperlex/intake/sources.py` (`ROUTE_PRESETS` around line 103, and the unknown-route error f-string around line 167)
- Test: `tests/test_trends_evidence.py`

**Interfaces:**
- Consumes: `pick_source`, `resolve_source`, `list_sources`.
- Produces: `ROUTE_PRESETS["trends"]` with `source="combined"`, `network=True`, and a description. Unknown-route `error` text contains the substring `trends`. `pick_source(None, route="trends", force_offline=False)` returns source `combined` and `route == "trends"`. `force_offline=True` returns source `mock`, `offline_forced is True`, and `route == "trends"`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_trends_evidence.py`:

```python
def test_route_trends_selects_combined():
    from hyperlex.intake.sources import list_sources, pick_source, resolve_source

    src, pkt = pick_source(None, route="trends", force_offline=False)
    assert src == "combined"
    assert pkt["route"] == "trends"
    assert pkt["ok"] is True
    assert pkt["network"] is True

    src_off, pkt_off = pick_source(None, route="trends", force_offline=True)
    assert src_off == "mock"
    assert pkt_off["offline_forced"] is True
    assert pkt_off["route"] == "trends"

    names = {row["name"] for row in list_sources()["routes"]}
    assert "trends" in names

    unknown = resolve_source(route="not-a-route", force_offline=False)
    assert unknown["ok"] is False
    assert "trends" in unknown["error"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_trends_evidence.py::test_route_trends_selects_combined -v`

Expected: FAIL. `unknown route='trends'` (the preset does not exist yet), or the unknown-route error string lacks `trends` if the preset was added without the error text.

- [ ] **Step 3: Write minimal implementation**

Add this entry to `ROUTE_PRESETS` after the `social` entry:

```python
    "trends": {
        "source": "combined",
        "description": "Combined language ingest plus a Google Trends evidence packet",
        "network": True,
    },
```

Change the unknown-route error to:

```python
"error": f"unknown route={route_name!r}; use offline|mock|default|live|glossary|social|trends",
```

Do not add `trends` to `SOURCE_CATALOG`. It is a route, not a text source.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_trends_evidence.py::test_route_trends_selects_combined tests/test_ingest_routes.py -v`

Expected: PASS. Existing route tests still pass.

- [ ] **Step 5: Commit**

```bash
git add src/hyperlex/intake/sources.py tests/test_trends_evidence.py
git commit -m "feat: add trends route preset"
```

---

### Task 3: Evidence packet builder

**Files:**
- Create: `src/hyperlex/intake/trends.py`
- Create: `tests/fixtures/trends_rizz.json`
- Test: `tests/test_trends_evidence.py`

**Interfaces:**
- Consumes: `hyperlex.provenance.source_fingerprint`.
- Produces:

```python
PACKET_KEYS: tuple[str, ...]  # the 17 keys listed in Step 3

def build_trends_packet(
    *,
    query: str,
    geo: str,
    timeframe: str,
    interest_over_time: list | None = None,
    related_queries: dict | None = None,
    failure: str | None = None,
    error_class: str | None = None,
    cached: bool = False,
    fetched_at: str | None = None,
) -> dict:
    """Return a packet that has exactly PACKET_KEYS.

    failure set → status not_computable, that reason, empty lists,
    dropped_rows 0, truncated False, claims NOT_COMPUTABLE.
    failure None → normalize rows, then status ok or empty.
    """
```

- [ ] **Step 1: Write the failing test**

Create `tests/fixtures/trends_rizz.json`:

```json
{
  "interest_over_time": [
    {"date": "2026-06-21", "value": 42, "partial": false},
    {"date": "2026-06-28", "value": 100, "partial": true}
  ],
  "related_queries": {
    "top": [{"query": "rizz meaning", "value": 100}],
    "rising": [{"query": "rizz face", "value": "Breakout"}]
  }
}
```

Add `import json` and `from pathlib import Path` to the imports at the top of `tests/test_trends_evidence.py`. Then append:

```python
FIXTURE = json.loads(
    (Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "trends_rizz.json").read_text(
        encoding="utf-8"
    )
)

PACKET_KEYS = {
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
}


def test_build_ok_packet_from_fixture():
    from hyperlex.intake.trends import PACKET_KEYS as KEYS
    from hyperlex.intake.trends import build_trends_packet

    packet = build_trends_packet(
        query="Rizz",
        geo="",
        timeframe="today 3-m",
        interest_over_time=FIXTURE["interest_over_time"],
        related_queries=FIXTURE["related_queries"],
        fetched_at="2026-09-22T00:00:00+00:00",
    )
    assert set(packet) == set(KEYS) == PACKET_KEYS
    assert packet["schema"] == "hyperlex.trends_evidence.v1"
    assert packet["status"] == "ok"
    assert packet["reason"] is None
    assert packet["query"] == "Rizz"
    assert packet["brier"] is None
    assert packet["error_class"] is None
    assert packet["cached"] is False
    assert packet["dropped_rows"] == 0
    assert packet["truncated"] is False
    assert packet["related_queries"]["rising"][0]["value"] == "Breakout"
    assert packet["interest_over_time"][0]["value"] == 42
    assert packet["scale"]["interest"] == "relative_0_100_within_this_request"
    assert "not probabilities" in packet["scale"]["note"]
    assert packet["claims"] == [
        {"statement": "interest_over_time", "label": "OBSERVED"},
        {"statement": "related_queries", "label": "OBSERVED"},
    ]
    fp = packet["source_fingerprint"]
    assert fp["source"] == "trends"
    assert fp["source_locator"] == "hyperlex://trends?geo=&timeframe=today%203-m"
    assert fp["fetched_at"] == "2026-09-22T00:00:00+00:00"


def test_build_packet_coerces_whole_numbers_and_drops_bad_points():
    from hyperlex.intake.trends import build_trends_packet

    packet = build_trends_packet(
        query="rizz",
        geo="US",
        timeframe="now 7-d",
        interest_over_time=[
            {"date": "2026-09-01", "value": 42.0, "partial": 0},
            {"date": "2026-09-02", "value": 100, "partial": True},
            {"date": "2026-09-03", "value": 101, "partial": False},
            {"date": "2026-09-04", "value": -1, "partial": False},
            {"date": "2026-09-05", "value": float("nan"), "partial": False},
            {"value": 10, "partial": False},
        ],
        related_queries={"top": [{"query": "rizz meaning", "value": 50.0}], "rising": []},
        fetched_at="2026-09-22T00:00:00+00:00",
    )
    assert [row["value"] for row in packet["interest_over_time"]] == [42, 100]
    assert packet["interest_over_time"][0]["partial"] is False
    assert packet["interest_over_time"][1]["partial"] is True
    assert packet["dropped_rows"] == 4
    assert packet["related_queries"]["top"][0]["value"] == 50
    assert packet["status"] == "ok"
    assert packet["source_fingerprint"]["source_locator"] == (
        "hyperlex://trends?geo=US&timeframe=now%207-d"
    )


def test_build_packet_empty_when_nothing_remains():
    from hyperlex.intake.trends import build_trends_packet

    packet = build_trends_packet(
        query="rizz",
        geo="",
        timeframe="today 3-m",
        interest_over_time=[{"date": "2026-09-01", "value": 101, "partial": False}],
        related_queries={"top": [], "rising": []},
        fetched_at="2026-09-22T00:00:00+00:00",
    )
    assert packet["status"] == "empty"
    assert packet["reason"] == "below_trends_threshold"
    assert packet["interest_over_time"] == []
    assert packet["dropped_rows"] == 1
    assert packet["claims"][0]["label"] == "OBSERVED"
    assert packet["brier"] is None


def test_build_packet_caps_related_queries():
    from hyperlex.intake.trends import build_trends_packet

    top = [{"query": f"q{i}", "value": i} for i in range(26)]
    packet = build_trends_packet(
        query="rizz",
        geo="",
        timeframe="today 3-m",
        interest_over_time=[],
        related_queries={"top": top, "rising": []},
        fetched_at="2026-09-22T00:00:00+00:00",
    )
    assert packet["status"] == "ok"
    assert len(packet["related_queries"]["top"]) == 25
    assert packet["truncated"] is True
    assert packet["related_queries"]["top"][0]["query"] == "q0"


def test_build_failure_packet_is_not_computable():
    from hyperlex.intake.trends import build_trends_packet

    packet = build_trends_packet(
        query="rizz",
        geo="",
        timeframe="today 3-m",
        failure="offline",
        fetched_at="2026-09-22T00:00:00+00:00",
    )
    assert packet["status"] == "not_computable"
    assert packet["reason"] == "offline"
    assert packet["interest_over_time"] == []
    assert packet["related_queries"] == {"top": [], "rising": []}
    assert packet["dropped_rows"] == 0
    assert packet["truncated"] is False
    assert packet["error_class"] is None
    assert packet["brier"] is None
    assert packet["claims"] == [
        {"statement": "interest_over_time", "label": "NOT_COMPUTABLE"},
        {"statement": "related_queries", "label": "NOT_COMPUTABLE"},
    ]
    assert packet["source_fingerprint"]["fingerprint_id"]

    failed = build_trends_packet(
        query="rizz",
        geo="",
        timeframe="today 3-m",
        failure="fetch_failed",
        error_class="RuntimeError",
        fetched_at="2026-09-22T00:00:00+00:00",
    )
    assert failed["reason"] == "fetch_failed"
    assert failed["error_class"] == "RuntimeError"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_trends_evidence.py::test_build_ok_packet_from_fixture tests/test_trends_evidence.py::test_build_packet_coerces_whole_numbers_and_drops_bad_points tests/test_trends_evidence.py::test_build_packet_empty_when_nothing_remains tests/test_trends_evidence.py::test_build_packet_caps_related_queries tests/test_trends_evidence.py::test_build_failure_packet_is_not_computable -v`

Expected: FAIL with `ModuleNotFoundError: hyperlex.intake.trends`.

- [ ] **Step 3: Write minimal implementation**

Create `src/hyperlex/intake/trends.py` with the builder only. Task 4 adds `attach_trends` and `PytrendsClient` to this file.

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_trends_evidence.py -v`

Expected: PASS. Task 1 and Task 2 tests still pass.

- [ ] **Step 5: Commit**

```bash
git add src/hyperlex/intake/trends.py tests/fixtures/trends_rizz.json tests/test_trends_evidence.py
git commit -m "feat: build trends evidence packets"
```

---

### Task 4: `attach_trends` decision order and pytrends client

**Files:**
- Modify: `src/hyperlex/intake/trends.py` (append; leave `build_trends_packet` as Task 3 wrote it)
- Test: `tests/test_trends_evidence.py`

**Interfaces:**
- Consumes: `build_trends_packet`, `PACKET_KEYS`, `rate_window_open`, `stamp_rate_limit`, `cache_key`, `get_cached`, `set_cached` from `hyperlex.intake.cache`, `offline_mode` from `hyperlex.intake.sources`.
- Produces:

```python
def trends_geo_timeframe() -> tuple[str, str]:
    """(geo, timeframe) from HYPERLEX_TRENDS_GEO and HYPERLEX_TRENDS_TIMEFRAME."""

def pytrends_import_status() -> str:
    """'ok' or 'missing'. Any exception other than ModuleNotFoundError propagates."""

def attach_trends(
    ingest: dict,
    *,
    route: str | None,
    offline: bool | None = None,
    client: object | None = None,
) -> dict:
    """Return the same dict. Maybe set ingest['trends']. Do not change other keys.

    Decision order from the spec. Skip the extra check when client is not None.
    Offline when offline is True or offline_mode() is True.
    """

class PytrendsClient:
    def fetch(self, query: str, *, geo: str, timeframe: str) -> dict:
        """One keyword. Raises on transport failure. Empty lists mean no rows."""
```

`client.fetch` returns `{"interest_over_time": list, "related_queries": {"top": list, "rising": list}}` in the row shape `build_trends_packet` already accepts.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_trends_evidence.py`:

```python
class _Boom:
    def __init__(self):
        self.calls = 0

    def fetch(self, query, *, geo, timeframe):
        self.calls += 1
        raise AssertionError(f"client should not be called for {query}")


class _Fixture:
    def __init__(self, payload=None):
        self.calls = 0
        self.payload = payload if payload is not None else FIXTURE

    def fetch(self, query, *, geo, timeframe):
        self.calls += 1
        self.query = query
        self.geo = geo
        self.timeframe = timeframe
        return self.payload


class _Raise:
    def __init__(self, exc):
        self.exc = exc
        self.calls = 0

    def fetch(self, query, *, geo, timeframe):
        self.calls += 1
        raise self.exc


def _base(query="Rizz"):
    return {
        "query": query,
        "raw_signal": "LANGUAGE",
        "extracted_terms": ["rizz"],
        "source_fingerprint": {"fingerprint_id": "lang-fp"},
    }


def test_attach_ignores_other_routes(trends_env):
    from hyperlex.intake.trends import attach_trends

    client = _Boom()
    ingest = _base()
    out = attach_trends(ingest, route="glossary", offline=False, client=client)
    assert "trends" not in out
    assert out["raw_signal"] == "LANGUAGE"
    assert client.calls == 0
    assert attach_trends(_base(), route=None, offline=False, client=client)["raw_signal"] == "LANGUAGE"


def test_attach_offline_trends_and_live(trends_env):
    from hyperlex.intake.trends import attach_trends

    client = _Boom()
    trends = attach_trends(_base(), route="trends", offline=True, client=client)
    assert trends["trends"]["status"] == "not_computable"
    assert trends["trends"]["reason"] == "offline"
    assert trends["trends"]["brier"] is None
    assert trends["source_fingerprint"]["fingerprint_id"] == "lang-fp"
    assert trends["raw_signal"] == "LANGUAGE"

    live = attach_trends(_base(), route="live", offline=True, client=client)
    assert "trends" not in live
    assert client.calls == 0


def test_attach_missing_extra(trends_env, monkeypatch):
    from hyperlex.intake import trends as trends_mod

    monkeypatch.setattr(trends_mod, "pytrends_import_status", lambda: "missing")
    trends = trends_mod.attach_trends(_base(), route="trends", offline=False, client=None)
    assert trends["trends"]["reason"] == "trends_extra_missing"
    live = trends_mod.attach_trends(_base(), route="live", offline=False, client=None)
    assert "trends" not in live


def test_attach_broken_import(trends_env, monkeypatch):
    from hyperlex.intake import trends as trends_mod

    def _boom():
        raise RuntimeError("import exploded")

    monkeypatch.setattr(trends_mod, "pytrends_import_status", _boom)
    for route in ("trends", "live"):
        out = trends_mod.attach_trends(_base(), route=route, offline=False, client=None)
        assert out["trends"]["reason"] == "fetch_failed"
        assert out["trends"]["error_class"] == "RuntimeError"
        assert "import exploded" not in json.dumps(out["trends"])


def test_attach_rejects_query_length(trends_env):
    from hyperlex.intake.trends import attach_trends

    client = _Boom()
    empty = attach_trends(_base("   "), route="trends", offline=False, client=client)
    assert empty["trends"]["reason"] == "query_rejected"
    long = attach_trends(_base("a" * 101), route="trends", offline=False, client=client)
    assert long["trends"]["reason"] == "query_rejected"
    assert client.calls == 0

    ok_len = _Fixture({"interest_over_time": [], "related_queries": {"top": [], "rising": []}})
    allowed = attach_trends(_base("b" * 100), route="trends", offline=False, client=ok_len)
    assert allowed["trends"]["reason"] != "query_rejected"
    assert ok_len.calls == 1
    assert ok_len.query == "b" * 100


def test_attach_fixture_caches_and_second_call_skips_client(trends_env, monkeypatch):
    from hyperlex.intake import trends as trends_mod

    stamps = {"n": 0}

    def _stamp(source):
        stamps["n"] += 1

    monkeypatch.setattr(trends_mod, "stamp_rate_limit", _stamp)
    client = _Fixture()
    first = trends_mod.attach_trends(_base(" Rizz "), route="trends", offline=False, client=client)
    assert first["trends"]["status"] == "ok"
    assert first["trends"]["query"] == "Rizz"
    assert first["trends"]["cached"] is False
    assert first["trends"]["related_queries"]["rising"][0]["value"] == "Breakout"
    assert first["raw_signal"] == "LANGUAGE"
    assert first["source_fingerprint"]["fingerprint_id"] == "lang-fp"
    assert client.calls == 1
    assert stamps["n"] == 1

    second = trends_mod.attach_trends(_base("Rizz"), route="live", offline=False, client=_Boom())
    assert second["trends"]["cached"] is True
    assert second["trends"]["status"] == "ok"
    assert second["trends"]["fetched_at"] == first["trends"]["fetched_at"]
    assert stamps["n"] == 1
    from hyperlex.intake.cache import cache_key, get_cached

    stored = json.loads(get_cached(cache_key("rizz||today 3-m", "trends"), source="trends"))
    assert stored["cached"] is False


def test_attach_rate_window_closed(trends_env, monkeypatch):
    from hyperlex.intake import trends as trends_mod

    monkeypatch.setattr(trends_mod, "rate_window_open", lambda source: False)
    client = _Boom()
    out = trends_mod.attach_trends(_base(), route="trends", offline=False, client=client)
    assert out["trends"]["reason"] == "rate_limited"
    assert client.calls == 0


def test_attach_empty_answer_is_cached(trends_env, monkeypatch):
    from hyperlex.intake.cache import get_cached, cache_key
    from hyperlex.intake.trends import attach_trends

    monkeypatch.setattr("hyperlex.intake.trends.stamp_rate_limit", lambda source: None)
    client = _Fixture({"interest_over_time": [], "related_queries": {"top": [], "rising": []}})
    out = attach_trends(_base("rizz"), route="trends", offline=False, client=client)
    assert out["trends"]["status"] == "empty"
    assert out["trends"]["reason"] == "below_trends_threshold"
    stored = get_cached(cache_key("rizz||today 3-m", "trends"), source="trends")
    assert stored is not None
    assert json.loads(stored)["status"] == "empty"


def test_attach_fetch_failed_is_not_cached_but_stamps(trends_env, monkeypatch, capsys):
    from hyperlex.intake.cache import cache_key, get_cached
    from hyperlex.intake import trends as trends_mod

    stamps = {"n": 0}
    monkeypatch.setattr(trends_mod, "stamp_rate_limit", lambda source: stamps.__setitem__("n", stamps["n"] + 1))
    out = trends_mod.attach_trends(
        _base("rizz"),
        route="live",
        offline=False,
        client=_Raise(RuntimeError("socket down")),
    )
    assert out["trends"]["reason"] == "fetch_failed"
    assert out["trends"]["error_class"] == "RuntimeError"
    assert "socket down" not in json.dumps(out["trends"])
    assert stamps["n"] == 1
    assert get_cached(cache_key("rizz||today 3-m", "trends"), source="trends") is None
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_attach_429_is_rate_limited_and_stamps(trends_env, monkeypatch):
    from hyperlex.intake import trends as trends_mod

    stamps = {"n": 0}
    monkeypatch.setattr(trends_mod, "stamp_rate_limit", lambda source: stamps.__setitem__("n", stamps["n"] + 1))

    class _Resp:
        status_code = 429

    class _HTTPError(Exception):
        def __init__(self):
            super().__init__("ignored body")
            self.response = _Resp()

    by_status = trends_mod.attach_trends(
        _base("rizz"), route="trends", offline=False, client=_Raise(_HTTPError())
    )
    assert by_status["trends"]["reason"] == "rate_limited"
    assert by_status["trends"]["error_class"] is None
    assert "ignored body" not in json.dumps(by_status["trends"])

    by_message = trends_mod.attach_trends(
        _base("rizz"),
        route="trends",
        offline=False,
        client=_Raise(RuntimeError("Google returned a response with code 429")),
    )
    assert by_message["trends"]["reason"] == "rate_limited"
    assert stamps["n"] == 2


def test_geo_and_timeframe_env(trends_env, monkeypatch):
    from hyperlex.intake.trends import attach_trends

    monkeypatch.setenv("HYPERLEX_NO_RATE_LIMIT", "1")
    monkeypatch.setenv("HYPERLEX_TRENDS_GEO", "  US  ")
    monkeypatch.setenv("HYPERLEX_TRENDS_TIMEFRAME", "now 7-d")
    client = _Fixture()
    out = attach_trends(_base("rizz"), route="trends", offline=False, client=client)
    assert client.calls == 1
    assert client.geo == "US"
    assert client.timeframe == "now 7-d"
    assert out["trends"]["geo"] == "US"
    assert out["trends"]["timeframe"] == "now 7-d"
    assert out["trends"]["source_fingerprint"]["source_locator"] == (
        "hyperlex://trends?geo=US&timeframe=now%207-d"
    )

    monkeypatch.setenv("HYPERLEX_TRENDS_GEO", "   ")
    blank = attach_trends(_base("other"), route="trends", offline=False, client=_Fixture())
    assert blank["trends"]["geo"] == ""


def test_pytrends_import_status_missing(monkeypatch):
    from hyperlex.intake import trends as trends_mod

    monkeypatch.setattr(trends_mod, "find_spec", lambda name: None)
    assert trends_mod.pytrends_import_status() == "missing"


def test_pytrends_client_maps_frames(monkeypatch):
    from hyperlex.intake.trends import PytrendsClient

    class _Row(dict):
        pass

    class _Frame:
        def __init__(self, columns, index, rows):
            self.columns = columns
            self.empty = len(rows) == 0
            self._index = index
            self._rows = rows

        def iterrows(self):
            for idx, row in zip(self._index, self._rows):
                yield idx, _Row(row)

    class _Req:
        def __init__(self):
            self.kwargs = None

        def build_payload(self, kws, timeframe, geo):
            self.kwargs = {"kw_list": kws, "timeframe": timeframe, "geo": geo}

        def interest_over_time(self):
            return _Frame(
                ["rizz", "isPartial"],
                ["2026-06-21"],
                [{"rizz": 42, "isPartial": False}],
            )

        def related_queries(self):
            top = _Frame(["query", "value"], [0], [{"query": "rizz meaning", "value": 100}])
            rising = _Frame(["query", "value"], [0], [{"query": "rizz face", "value": "Breakout"}])
            return {"rizz": {"top": top, "rising": rising}}

    req = _Req()
    monkeypatch.setattr("hyperlex.intake.trends._new_trend_req", lambda: req)
    got = PytrendsClient().fetch("rizz", geo="", timeframe="today 3-m")
    assert req.kwargs == {"kw_list": ["rizz"], "timeframe": "today 3-m", "geo": ""}
    assert got["interest_over_time"] == [{"date": "2026-06-21", "value": 42, "partial": False}]
    assert got["related_queries"]["rising"][0]["value"] == "Breakout"
```

The cache-key tests assume `cache_key(f"{query}|{geo}|{timeframe}", "trends")` lowercases the whole query argument. For query `rizz`, geo `""`, timeframe `today 3-m`, the key is `trends:rizz||today 3-m`.

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_trends_evidence.py::test_attach_ignores_other_routes tests/test_trends_evidence.py::test_attach_offline_trends_and_live tests/test_trends_evidence.py::test_attach_missing_extra tests/test_trends_evidence.py::test_attach_fixture_caches_and_second_call_skips_client tests/test_trends_evidence.py::test_pytrends_client_maps_frames -v`

Expected: FAIL with `ImportError` on `attach_trends` or `PytrendsClient`.

- [ ] **Step 3: Write minimal implementation**

Append to `src/hyperlex/intake/trends.py`:

```python
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
```

Add `Any` to the typing import if Task 3's import line does not already include it. It does.

The outer `attach_trends` try/except is a backstop so a cache or builder bug cannot escape. Expected failures are caught inside `_attach_trends` before they reach it. The backstop still returns a packet and does not print.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_trends_evidence.py -v`

Expected: PASS. No test imports pytrends. Confirm with:

Run: `PYTHONPATH=src python -c "import hyperlex.intake.trends, sys; assert 'pytrends' not in sys.modules"`

Expected: exit 0.

- [ ] **Step 5: Commit**

```bash
git add src/hyperlex/intake/trends.py tests/test_trends_evidence.py
git commit -m "feat: attach trends evidence from an injected client"
```

---

### Task 5: Wire ingest, analysis, docs, and the optional extra

**Files:**
- Modify: `src/hyperlex/intake/__init__.py` (the `return { ... }` at the end of `fetch_ingest`, about lines 324–343)
- Modify: `src/hyperlex/analysis/__init__.py` (after `result["ingest"] = {...}` ends, about line 1125, and before the `if validate:` block)
- Modify: `pyproject.toml` (`[project.optional-dependencies]`)
- Modify: `docs/modules/ingest.md` (the route table around lines 13–17, plus a short paragraph under Cache & rate limits)
- Modify: `scripts/hyperlex.py` help strings that list routes (lines 921, 2415, 2437, 2509, 2965)
- Test: `tests/test_trends_evidence.py`

**Interfaces:**
- Consumes: `attach_trends(ingest, *, route, offline, client=None) -> dict`.
- Produces: `fetch_ingest(..., route="trends")` under `HYPERLEX_OFFLINE=1` includes `trends.reason == "offline"` and language source `mock`. `detect_memetic_patterns` copies a monkeypatched `trends` object to `result["trends"]` and leaves it out of `result["ingest"]` and `result["analysis"]`. `pyproject` extra `trends = ["pytrends>=4.9"]`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_trends_evidence.py`:

```python
def test_fetch_ingest_offline_trends_and_mock_omits(trends_env, monkeypatch):
    from hyperlex.intake import fetch_ingest

    monkeypatch.setenv("HYPERLEX_OFFLINE", "1")
    trends = fetch_ingest("rizz", route="trends")
    assert trends["source"] == "mock"
    assert trends["trends"]["status"] == "not_computable"
    assert trends["trends"]["reason"] == "offline"
    assert "brainrot" in trends["raw_signal"]
    fp = trends["source_fingerprint"]["fingerprint_id"]

    again = fetch_ingest("rizz", source="mock")
    assert "trends" not in again
    offline = fetch_ingest("rizz", route="offline")
    assert "trends" not in offline
    assert fp


def test_detect_copies_trends_to_top_level(monkeypatch):
    from hyperlex.analysis import detect_memetic_patterns

    sentinel = {
        "schema": "hyperlex.trends_evidence.v1",
        "status": "ok",
        "brier": None,
    }

    def _fake_fetch(query, source="mock", structured=True, max_terms=8, route=None):
        return {
            "query": query,
            "source": "mock",
            "raw_signal": 'Mock channel note on "rizz". Quiet discourse sample.',
            "extracted_terms": [],
            "metadata": {},
            "route": {"route": "trends", "ok": True},
            "provenance": {"source_fingerprint": {"fingerprint_id": "abc"}},
            "source_fingerprint": {
                "fingerprint_id": "abc",
                "content_hash": "abc",
                "source_locator": "hyperlex://mock",
                "adapter_version": "ingest-v1.7",
            },
            "trends": sentinel,
        }

    monkeypatch.setattr("hyperlex.analysis.fetch_ingest", _fake_fetch)
    result = detect_memetic_patterns(query="rizz", ingest_source="mock", ingest_route="trends")
    assert result["trends"] is sentinel
    assert "trends" not in result["ingest"]
    assert "trends" not in result["analysis"]
    assert result["provenance"]["brier"] is None


def test_cli_run_trends_offline(tmp_path):
    import os
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[1]
    env = {
        **dict(os.environ),
        "PYTHONPATH": str(root / "src"),
        "HYPERLEX_OFFLINE": "1",
        "HYPERLEX_SCORE_LOG": str(tmp_path / "score_log.jsonl"),
        "HYPERLEX_CACHE_DIR": str(tmp_path / "cache"),
        "HYPERLEX_RATE_LIMIT_PATH": str(tmp_path / "rate_limit.json"),
    }
    proc = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "hyperlex.py"),
            "run",
            "rizz",
            "--route",
            "trends",
            "--no-phase5",
            "--receipt-dir",
            str(tmp_path / "receipts"),
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads(proc.stdout)
    assert data["result"]["trends"]["status"] == "not_computable"
    assert data["result"]["trends"]["reason"] == "offline"
    assert data["result"]["provenance"]["brier"] is None
```

`brainrot` is the mock language string for `rizz` from `ingest_signal`. Its presence shows the Trends packet did not replace the language text.

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_trends_evidence.py::test_fetch_ingest_offline_trends_and_mock_omits tests/test_trends_evidence.py::test_detect_copies_trends_to_top_level tests/test_trends_evidence.py::test_cli_run_trends_offline -v`

Expected: FAIL. `fetch_ingest` has no `trends` key. `detect_memetic_patterns` drops the sentinel. The CLI JSON has no `result.trends`.

- [ ] **Step 3: Write minimal implementation**

In `fetch_ingest`, replace the bare `return { ... }` with a named dict and a call. Add the import at the top of `src/hyperlex/intake/__init__.py` next to `from .sources import pick_source`:

```python
from .trends import attach_trends
```

Then:

```python
    packet = {
        "query": query,
        "source": source,
        "raw_signal": raw,
        "extracted_terms": terms,
        "route": resolved,
        "metadata": {
            "source_type": "real" if source in ("real", "glossary", "urban", "reddit", "wikipedia", "moltbook", "agent_discourse", "moltbook_memory") else "synthetic_stub",
            "cached": _cache_key(query, source) in _CACHE,
            "fetched_at": fetched_at,
            "route": resolved.get("route"),
        },
        "provenance": {
            "version": "1.6.0",
            "ingest_source": source,
            "route": resolved.get("route"),
            "source_fingerprint": fp,
        },
        "source_fingerprint": fp,
    }
    return attach_trends(
        packet,
        route=resolved.get("route"),
        offline=bool(resolved.get("offline_forced")),
    )
```

In `detect_memetic_patterns`, immediately after the `result["ingest"] = { ... }` block and before `if validate:`:

```python
    if "trends" in ingest_data:
        result["trends"] = ingest_data["trends"]
```

In `pyproject.toml`, inside `[project.optional-dependencies]`, add:

```toml
trends = [
    "pytrends>=4.9",
]
```

In `docs/modules/ingest.md`, add a row to the route table:

```markdown
| `trends` | `combined` | yes |
```

Under the Cache & rate limits section, add:

```markdown
`--route trends` always attaches a `trends` evidence packet (`hyperlex.trends_evidence.v1`). `--route live` attaches the same packet when the `trends` extra imports and the process is online. Install with `pip install -e ".[trends]"`. Geo defaults to worldwide (`HYPERLEX_TRENDS_GEO`). Timeframe defaults to `today 3-m` (`HYPERLEX_TRENDS_TIMEFRAME`). Minimum interval defaults to 60 seconds (`HYPERLEX_SOURCE_MIN_INTERVAL_TRENDS`). The packet is observed search interest. It does not change virality or Brier.
```

In `scripts/hyperlex.py`, change these five strings and nothing else about routing:

- Line 921 command-map why: `Catalog + routes (offline|live|default|glossary|social|trends)`
- Line 2415 sources help: `List ingest sources + routes (offline|live|default|glossary|social|trends)`
- Line 2438 pipeline route help: `Operator route: offline|mock|default|live|glossary|social|trends`
- Line 2509 analyze route help: same operator-route string as line 2438
- Line 2965 scan route help: same operator-route string as line 2438

Do not change route defaults.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_trends_evidence.py tests/test_ingest_routes.py tests/test_pipeline.py -v`

Expected: PASS. `test_cli_run_one_shot` still exits 0 on `--route offline` and does not require a `trends` key.

If `test_pipeline.py` hits the network, re-run it the way CI does. Do not add a live Trends call to make it pass.

- [ ] **Step 5: Commit**

```bash
git add src/hyperlex/intake/__init__.py src/hyperlex/analysis/__init__.py pyproject.toml docs/modules/ingest.md scripts/hyperlex.py tests/test_trends_evidence.py
git commit -m "feat: wire trends evidence into analyze and run"
```
