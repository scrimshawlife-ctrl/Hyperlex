"""ledger-stats + openai_compatible provider guards."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from hyperlex import emit_receipt, detect_memetic_patterns, ledger_stats
from hyperlex.llm.governed import (
    get_provider,
    set_provider,
    enrich_neologisms,
    GovernedLLMError,
    _openai_compatible_provider,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "hyperlex.py"


def test_ledger_stats_from_emitted(tmp_path: Path) -> None:
    ledger = tmp_path / "rl.jsonl"
    out = tmp_path / "r"
    for q in ("sharp steam revenge", "hodl degen rekt", "weather mild"):
        result = detect_memetic_patterns(query=q, ingest_source="mock")
        emit_receipt(result, out_dir=out, append_ledger=True, ledger_path=ledger)
    stats = ledger_stats(ledger)
    assert stats["n_entries"] == 3
    assert stats["chain_ok"] is True
    assert stats["schema"] == "hyperlex.ledger_stats.v1"
    assert "families" in stats
    assert stats["n_with_lineage"] >= 1


def test_ledger_stats_cli(tmp_path: Path) -> None:
    ledger = tmp_path / "rl.jsonl"
    result = detect_memetic_patterns(query="sharp steam", ingest_source="mock")
    emit_receipt(result, out_dir=tmp_path / "r", append_ledger=True, ledger_path=ledger)
    env = os.environ.copy()
    env["HYPERLEX_OFFLINE"] = "1"
    env["PYTHONPATH"] = str(ROOT / "src")
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "ledger-stats", "--ledger", str(ledger)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
    )
    assert r.returncode == 0, r.stderr
    body = json.loads(r.stdout)
    assert body["ok"] is True
    assert body["n_entries"] >= 1


def test_openai_provider_selected(monkeypatch) -> None:
    monkeypatch.setenv("HYPERLEX_LLM_PROVIDER", "openai_compatible")
    set_provider(None)
    p = get_provider()
    assert p is _openai_compatible_provider


def test_openai_provider_offline_fail_closed(monkeypatch) -> None:
    monkeypatch.setenv("HYPERLEX_OFFLINE", "1")
    monkeypatch.setenv("HYPERLEX_LLM_API_KEY", "sk-test")
    with pytest.raises(GovernedLLMError, match="offline"):
        _openai_compatible_provider("prompt", {"text": "hello"})


def test_openai_provider_missing_key(monkeypatch) -> None:
    monkeypatch.delenv("HYPERLEX_OFFLINE", raising=False)
    monkeypatch.setenv("HYPERLEX_OFFLINE", "0")
    monkeypatch.delenv("HYPERLEX_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(GovernedLLMError, match="API_KEY"):
        _openai_compatible_provider("prompt", {"text": "hello"})


def test_enrich_surfaces_openai_error(monkeypatch) -> None:
    monkeypatch.setenv("HYPERLEX_LLM", "1")
    monkeypatch.setenv("HYPERLEX_LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("HYPERLEX_OFFLINE", "1")
    monkeypatch.setenv("HYPERLEX_LLM_API_KEY", "sk-test")
    set_provider(None)
    out = enrich_neologisms("alpha beta gamma")
    # provider raises → enrich reports error, does not invent scores
    assert out["applied"] is False
    assert out["status"] == "error"
