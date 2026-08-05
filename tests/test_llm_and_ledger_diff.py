"""Governed LLM stub + ledger-diff CLI."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from hyperlex import detect_memetic_patterns
from hyperlex.llm.governed import (
    llm_enabled,
    enrich_neologisms,
    set_provider,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "hyperlex.py"
GOLDEN = ROOT / "examples" / "receipts" / "golden"


def test_llm_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("HYPERLEX_LLM", raising=False)
    assert llm_enabled() is False
    out = enrich_neologisms("sharp money degen", [{"term": "sharp", "formation": "x", "confidence": 0.5}])
    assert out["status"] == "skipped"
    assert out["applied"] is False


def test_llm_echo_provider(monkeypatch) -> None:
    monkeypatch.setenv("HYPERLEX_LLM", "1")
    monkeypatch.setenv("HYPERLEX_LLM_PROVIDER", "echo")
    set_provider(None)  # force env provider
    out = enrich_neologisms("alpha beta gamma delta epsilon zeta")
    assert out["status"] == "applied"
    assert out["applied"] is True
    assert out["n_new"] >= 1
    for c in out["candidates"]:
        assert c["provenance"] == "SPECULATIVE"
        assert c["confidence"] <= 0.85


def test_analyze_llm_enrichment_block(monkeypatch) -> None:
    monkeypatch.setenv("HYPERLEX_LLM", "1")
    monkeypatch.setenv("HYPERLEX_LLM_PROVIDER", "echo")
    set_provider(None)
    r = detect_memetic_patterns("alpha beta gamma delta epsilon", ingest_source="mock")
    assert r["provenance"]["brier"] is None
    block = r["analysis"].get("llm_enrichment")
    assert block is not None
    assert block["applied"] is True


def test_analyze_without_llm_has_no_block_or_skipped(monkeypatch) -> None:
    monkeypatch.delenv("HYPERLEX_LLM", raising=False)
    monkeypatch.delenv("HYPERLEX_LLM_PROVIDER", raising=False)
    set_provider(None)
    r = detect_memetic_patterns("sharp steam", ingest_source="mock")
    # when disabled, llm_enrichment may be absent
    block = r["analysis"].get("llm_enrichment")
    assert block is None or block.get("applied") is False


def test_ledger_diff_cli() -> None:
    a = GOLDEN / "betting-sharp.json"
    b = GOLDEN / "gaming-meta.json"
    env = os.environ.copy()
    env["HYPERLEX_OFFLINE"] = "1"
    env["PYTHONPATH"] = str(ROOT / "src")
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "ledger-diff", "--a", str(a), "--b", str(b)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
    )
    assert r.returncode == 0, r.stderr
    body = json.loads(r.stdout)
    assert body["ok"] is True
    assert body["same_integrity"] is False
    assert "lineage_family" in body["changed_fields"]
