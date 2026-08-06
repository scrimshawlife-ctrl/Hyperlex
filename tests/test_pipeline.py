"""Automatic backend pipeline: ingest → results (no auto-settle)."""

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
    "HYPERLEX_VECTOR": "0",
}


def test_run_pipeline_single_atom(tmp_path):
    from hyperlex.pipeline import run_pipeline

    log = tmp_path / "score_log.jsonl"
    receipts = tmp_path / "receipts"
    p = run_pipeline(
        "rizz",
        route="offline",
        log_path=log,
        receipt_dir=receipts,
        phase5=True,
    )
    assert p["schema"] == "hyperlex.pipeline_result.v1"
    assert p["ok"] is True
    assert p["n_atoms"] == 1
    assert p["brier"] is None
    assert p["n_forecasts"] >= 1
    assert p["receipt"]
    assert Path(p["receipt"]).is_file()
    assert p["result"]["provenance"]["brier"] is None
    assert p.get("phase5", {}).get("brier") is None
    assert log.is_file()


def test_run_pipeline_expands_multi_term(tmp_path):
    from hyperlex.pipeline import run_pipeline

    p = run_pipeline(
        "sigma rizz locked in",
        route="offline",
        log_path=tmp_path / "log.jsonl",
        receipt_dir=tmp_path / "r",
        phase5=True,
    )
    assert p["ok"] is True
    assert p["atoms"] == ["sigma", "rizz", "locked in"]
    assert p["n_atoms"] == 3
    assert p["n_receipts"] == 3
    assert p["n_forecasts"] >= 3
    assert p["brier"] is None
    for u in p["results"]:
        assert u["ok"] is True
        assert u["brier"] is None
        assert u.get("receipt")


def test_run_pipeline_no_expand(tmp_path):
    from hyperlex.pipeline import run_pipeline

    p = run_pipeline(
        "sigma rizz locked in",
        route="offline",
        expand_terms=False,
        log_path=tmp_path / "log.jsonl",
        receipt_dir=tmp_path / "r",
        phase5=False,
    )
    assert p["n_atoms"] == 1
    assert p["atoms"] == ["sigma rizz locked in"]


def test_pipeline_autoindexes_vector_on_ingest(tmp_path, monkeypatch):
    """Ingest/pipeline should fail-open index into the configured local vector store."""
    from hyperlex.pipeline import run_pipeline
    from hyperlex.vectordb import VectorStore, vector_search

    db = tmp_path / "auto.db"
    monkeypatch.setenv("HYPERLEX_VECTOR", "1")
    monkeypatch.setenv("HYPERLEX_VECTOR_BACKEND", "sqlite")
    monkeypatch.setenv("HYPERLEX_VECTOR_DB", str(db))
    monkeypatch.delenv("HYPERLEX_CHROMA_PATH", raising=False)

    p = run_pipeline(
        "rizz",
        route="offline",
        log_path=tmp_path / "log.jsonl",
        receipt_dir=tmp_path / "r",
        phase5=False,
    )
    assert p["ok"] is True
    unit = p["results"][0]
    assert "vector_index" in unit
    assert unit["vector_index"]["n_upserted"] >= 1
    assert unit["vector_index"]["brier"] is None
    assert db.is_file()
    with VectorStore(db) as store:
        assert store.count() >= 1
    hits = vector_search("rizz", path=db, kind="term", top_k=3, min_score=0.05)
    assert hits["ok"] is True
    assert hits["n_hits"] >= 1


def test_cli_pipeline_and_ingest_auto(tmp_path):
    env = {**ENV, "HYPERLEX_SCORE_LOG": str(tmp_path / "score.jsonl")}
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "hyperlex.py"),
            "pipeline",
            "rizz",
            "--route",
            "offline",
            "--receipt-dir",
            str(tmp_path / "rcpt"),
            "--no-phase5",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data["command"] == "pipeline"
    assert data["ok"] is True
    assert data["n_forecasts"] >= 1
    assert data["brier"] is None

    r2 = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "hyperlex.py"),
            "ingest",
            "locked in",
            "--route",
            "offline",
            "--receipt-dir",
            str(tmp_path / "rcpt2"),
            "--no-phase5",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r2.returncode == 0, r2.stderr + r2.stdout
    data2 = json.loads(r2.stdout)
    assert data2["command"] == "ingest"
    assert data2["ok"] is True
    assert data2.get("receipt") or data2.get("n_receipts", 0) >= 1


def test_cli_ingest_raw_only():
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "hyperlex.py"),
            "ingest",
            "rizz",
            "--raw-only",
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
    assert data["command"] == "ingest"
    assert data.get("mode") == "raw_only"
    assert "raw_signal" in (data.get("result") or {})


def test_cli_run_multi_term_compact(tmp_path):
    env = {**ENV, "HYPERLEX_SCORE_LOG": str(tmp_path / "s.jsonl")}
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "hyperlex.py"),
            "run",
            "sigma rizz locked in",
            "--route",
            "offline",
            "--receipt-dir",
            str(tmp_path / "r"),
            "--no-phase5",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data["command"] == "run"
    assert data["atoms"] == ["sigma", "rizz", "locked in"]
    assert data["n_atoms"] == 3
    # compact: full analysis bodies omitted
    assert "analysis" not in (data["results"][0] or {})
