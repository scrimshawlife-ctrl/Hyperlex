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
