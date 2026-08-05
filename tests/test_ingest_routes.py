"""Ingest source routing + simplified operator commands."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = {
    **dict(os.environ),
    "PYTHONPATH": str(ROOT / "src"),
    "HYPERLEX_OFFLINE": "1",
}


def test_resolve_aliases_and_routes():
    from hyperlex.intake.sources import pick_source, resolve_source, list_sources

    src, pkt = pick_source("real", force_offline=False)
    assert src == "glossary"
    assert pkt["known"] is True

    src, pkt = pick_source(None, route="live", force_offline=False)
    assert src == "combined"
    assert pkt["route"] == "live"

    src, pkt = pick_source("combined", force_offline=True)
    assert src == "mock"
    assert pkt["offline_forced"] is True

    cat = list_sources()
    assert cat["schema"] == "hyperlex.sources_catalog.v1"
    names = {s["name"] for s in cat["sources"]}
    assert "mock" in names and "combined" in names
    assert any(r["name"] == "offline" for r in cat["routes"])


def test_fetch_ingest_includes_route():
    from hyperlex.intake import fetch_ingest

    data = fetch_ingest("sharp steam revenge", source="mock")
    assert data["source"] == "mock"
    assert data["route"]["ok"] is True
    assert "raw_signal" in data
    assert data.get("source_fingerprint")


def test_cli_sources_and_commands():
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "hyperlex.py"), "sources", "--route", "offline"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=ENV,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data["ok"] is True
    assert data["resolve"]["source"] == "mock"

    r2 = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "hyperlex.py"), "commands"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=ENV,
    )
    assert r2.returncode == 0, r2.stderr + r2.stdout
    m = json.loads(r2.stdout)
    assert "daily_ops" in m
    assert m["schema"] == "hyperlex.command_map.v1"


def test_cli_run_one_shot(tmp_path):
    env = {**ENV, "HYPERLEX_SCORE_LOG": str(tmp_path / "score_log.jsonl")}
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "hyperlex.py"),
            "run",
            "sharp steam revenge",
            "--route",
            "offline",
            "--receipt-dir",
            str(tmp_path / "receipts"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data["command"] == "run"
    assert data["source"] == "mock"
    assert data.get("n_forecasts", 0) >= 1 or data.get("forecasts")
    assert data["result"]["provenance"]["brier"] is None

    r3 = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "hyperlex.py"), "pending", "--log", str(tmp_path / "score_log.jsonl")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r3.returncode == 0, r3.stderr + r3.stdout
    pend = json.loads(r3.stdout)
    assert pend["command"] == "pending"
    assert pend["n_open"] >= 1


def test_cli_analyze_positional():
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "hyperlex.py"),
            "analyze",
            "rizz locked in",
            "--route",
            "offline",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=ENV,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data["query"] == "rizz locked in"
    assert data["source"] == "mock"
