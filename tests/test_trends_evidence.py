"""Google Trends evidence packet. No network. No pytrends import."""

from __future__ import annotations

import json
import time
from pathlib import Path

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
    # L1 is process-global and is not keyed by HYPERLEX_CACHE_DIR.
    from hyperlex.intake.cache import clear_memory_cache

    clear_memory_cache()
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


def test_trends_extra_pins_urllib3_below_2():
    # pytrends 4.9.2 passes method_whitelist; urllib3 2 removed that argument.
    import tomllib

    path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    extra = data["project"]["optional-dependencies"]["trends"]
    assert "pytrends>=4.9" in extra
    assert "urllib3>=1.26,<2" in extra
