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
