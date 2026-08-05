"""Golden settled series + scan / cache unit tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from hyperlex.calibration import score_pair, score_series, NOT_COMPUTABLE
from hyperlex.intake.cache import (
    set_cached,
    get_cached,
    clear_memory_cache,
    cache_key,
    wait_for_rate_limit,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "hyperlex.py"
GOLDEN = ROOT / "examples" / "calibration" / "settled_series.v1.json"


def _cli(*args: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = __import__("os").environ.copy()
    env["HYPERLEX_OFFLINE"] = "1"
    env["HYPERLEX_NO_RATE_LIMIT"] = "1"
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=ROOT,
    )


def test_golden_settled_series_atomic_and_aggregate() -> None:
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    pairs = []
    for item in data["pairs"]:
        fc = item["forecast"]
        st = item["settlement"]
        rec = score_pair(fc, st)
        expected = item.get("expected_atomic")
        if expected is None:
            assert rec["status"] == NOT_COMPUTABLE
        else:
            assert rec["status"] == "SCORED"
            assert rec["atomic_score"] == pytest.approx(float(expected))
            pairs.append((fc, st))

    series = score_series(pairs, reference=data.get("reference", "climatology"))
    exp = data["expected_series"]
    assert series["status"] == exp["status"]
    assert series["n"] == exp["n"]
    assert series["series_brier"] == pytest.approx(float(exp["series_brier"]))

    empty = score_series([])
    assert empty["status"] == data["expected_empty"]["status"]
    assert empty["series_brier"] == NOT_COMPUTABLE


def test_disk_cache_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYPERLEX_CACHE_DIR", str(tmp_path / "cache"))
    clear_memory_cache()
    key = cache_key("sharp money", "glossary")
    assert get_cached(key, "glossary") is None
    set_cached(key, "signal-body", "glossary")
    clear_memory_cache()  # force L2 disk read
    assert get_cached(key, "glossary") == "signal-body"


def test_rate_limit_skip_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYPERLEX_NO_RATE_LIMIT", "1")
    info = wait_for_rate_limit("glossary")
    assert info["skipped"] is True
    assert info["waited"] == 0.0


def test_cli_scan_mock_with_receipt_and_forecasts(tmp_path: Path) -> None:
    out = tmp_path / "scan.json"
    ledger = tmp_path / "ledger.jsonl"
    log = tmp_path / "score.jsonl"
    receipts = tmp_path / "receipts"
    result = _cli(
        "scan",
        "--queries", "sharp steam revenge,brainrot aura mid",
        "--source", "mock",
        "--receipt",
        "--receipt-dir", str(receipts),
        "--ledger", str(ledger),
        "--forecasts",
        "--append-log",
        "--log", str(log),
        "--out", str(out),
    )
    assert result.returncode == 0, result.stderr + result.stdout
    body = json.loads(result.stdout)
    assert body["ok"] is True
    assert body["rune"] == "LIVE_EMERGENCE_SCAN"
    assert body["n_queries"] == 2
    assert body["n_ok"] == 2
    assert body["n_receipts"] == 2
    assert body["n_forecasts"] >= 1
    # no fabricated brier on any row
    for row in body["results"]:
        assert row["brier"] is None
    assert out.exists()
    assert ledger.exists()
    assert log.exists()


def test_cli_scan_default_config() -> None:
    result = _cli(
        "scan",
        "--config", str(ROOT / "examples" / "cron" / "scan-queries.json"),
        "--source", "mock",
    )
    assert result.returncode == 0, result.stderr + result.stdout
    body = json.loads(result.stdout)
    assert body["n_queries"] >= 3
    assert body["n_ok"] == body["n_queries"]
