"""Tests for relay, provenance fingerprints, glossary/x adapters."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from hyperlex import (
    detect_memetic_patterns,
    fetch_ingest,
    list_runes,
    relay_from_result,
    relay_forecasts,
    extract_forecasts,
    PKG_VERSION,
)
from hyperlex.provenance import source_fingerprint, content_fingerprint
from hyperlex.intake.x_search import fetch_x_search, fetch_x_stub
from hyperlex.intake.glossaries import list_glossaries, fetch_glossary

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "hyperlex.py"


def test_list_runes_catalog() -> None:
    runes = list_runes()
    ids = {r["rune_id"] for r in runes}
    assert "RUNE.HLX.LIVE_EMERGENCE_SCAN" in ids
    assert "RUNE.HLX.COMMUNICATION_RELAY" in ids
    assert "RUNE.HLX.CALIBRATION_FORECAST" in ids
    assert "RUNE.HLX.CALIBRATION_SERIES" in ids


def test_relay_from_result_envelopes() -> None:
    result = detect_memetic_patterns("sharp steam revenge", ingest_source="mock")
    envs = relay_from_result(result)
    assert len(envs) == 2
    rune_ids = {e["rune_id"] for e in envs}
    assert "RUNE.HLX.LIVE_EMERGENCE_SCAN" in rune_ids
    assert "RUNE.HLX.COMMUNICATION_RELAY" in rune_ids
    for e in envs:
        assert e["schema"] == "hyperlex.rune_envelope.v1"
        assert e["envelope_id"]
        # brier not fabricated
        assert e["provenance"].get("brier") is None


def test_relay_forecasts_not_computable_brier() -> None:
    result = detect_memetic_patterns("sharp steam", ingest_source="mock")
    fcs = extract_forecasts(result)
    env = relay_forecasts(fcs)
    assert env["rune_id"] == "RUNE.HLX.CALIBRATION_FORECAST"
    assert env["payload"]["brier"] is None
    labels = {c["statement"]: c["label"] for c in env["claims"]}
    assert labels["brier"] == "NOT_COMPUTABLE"


def test_source_fingerprint_stable() -> None:
    a = source_fingerprint(source="mock", query="q", raw_signal="hello", source_locator="loc")
    b = source_fingerprint(source="mock", query="q", raw_signal="hello", source_locator="loc")
    assert a["fingerprint_id"] == b["fingerprint_id"]
    assert a["content_hash"] == content_fingerprint("hello")
    c = source_fingerprint(source="mock", query="q", raw_signal="HELLO", source_locator="loc")
    assert c["fingerprint_id"] != a["fingerprint_id"]


def test_analysis_includes_source_fingerprint() -> None:
    result = detect_memetic_patterns("sharp steam", ingest_source="mock")
    fp = result["provenance"].get("source_fingerprint")
    assert fp is not None
    assert fp.get("fingerprint_id")
    assert fp.get("content_hash")
    assert result["provenance"].get("brier") is None
    assert "source_fingerprint" in (result.get("ingest") or {})


def test_fetch_ingest_fingerprint() -> None:
    data = fetch_ingest("test query", source="mock")
    assert "source_fingerprint" in data
    assert data["source_fingerprint"]["source"] == "mock"
    assert data["provenance"]["source_fingerprint"]["fingerprint_id"]


def test_glossaries_registry() -> None:
    gloss = list_glossaries()
    assert len(gloss) >= 3
    ids = {g["id"] for g in gloss}
    assert "action_network" in ids


def test_glossary_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYPERLEX_OFFLINE", "1")
    signal, locator, gid = fetch_glossary("sharp", glossary_id="action_network")
    assert "OFFLINE" in signal or "sharp" in signal.lower()
    assert gid == "action_network"
    assert locator


def test_x_search_stub_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HYPERLEX_X_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("TWITTER_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
    monkeypatch.setenv("HYPERLEX_OFFLINE", "0")
    signal, meta = fetch_x_search("memetic slang")
    assert "X_SEARCH" in signal or "stub" in meta.get("adapter", "")
    assert meta.get("live") is False
    # stub never claims observed market data without flagging
    assert meta.get("adapter") in ("stub", "x_api_v2", "xurl")


def test_cli_relay_list() -> None:
    env = __import__("os").environ.copy()
    env["HYPERLEX_OFFLINE"] = "1"
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "relay", "--list-runes"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
    )
    assert r.returncode == 0, r.stderr
    body = json.loads(r.stdout)
    assert body["ok"] is True
    assert len(body["runes"]) >= 4


def test_package_cli_check() -> None:
    env = __import__("os").environ.copy()
    env["HYPERLEX_OFFLINE"] = "1"
    env["PYTHONPATH"] = str(ROOT / "src")
    r = subprocess.run(
        [sys.executable, "-m", "hyperlex", "check"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    body = json.loads(r.stdout)
    assert body["ok"] is True
    assert body["version"] == PKG_VERSION
