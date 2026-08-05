"""Sanitized analysis archive export + static run history for Pages."""

from __future__ import annotations

import json
from pathlib import Path

from hyperlex import detect_memetic_patterns, emit_receipt, export_analysis_archive
from hyperlex.archive import (
    export_run_history,
    rebuild_archive_catalog,
    sanitize_phase5_summary,
    sanitize_receipt_summary,
)
from hyperlex.simulation import run_phase5_scenario


def test_sanitize_drops_brier_fabrication() -> None:
    r = detect_memetic_patterns("sharp steam", ingest_source="mock")
    s = sanitize_receipt_summary(r)
    assert s["brier"] is None
    assert s["epistemic"]["brier"] == "NOT_COMPUTABLE"
    assert "observed_preview" in s


def test_export_archive_bundle(tmp_path: Path) -> None:
    rec_dir = tmp_path / "receipts"
    ledger = tmp_path / "ledger.jsonl"
    for q in ("sharp steam", "nerf buff meta", "weather mild"):
        result = detect_memetic_patterns(query=q, ingest_source="mock")
        emit_receipt(result, out_dir=rec_dir, append_ledger=True, ledger_path=ledger)
    out = tmp_path / "archive"
    meta = export_analysis_archive(
        out_dir=out,
        ledger_path=ledger,
        receipt_dirs=[rec_dir],
        snapshot_id="test-snap",
    )
    assert meta["ok"] is True
    assert meta["n_receipt_summaries"] == 3
    idx = json.loads((out / "index.json").read_text())
    assert idx["schema"] == "hyperlex.analysis_archive.v1"
    assert idx["publish_safe"] is True
    assert (out / "index.md").exists()
    assert len(list((out / "receipts").glob("*.json"))) == 3


def test_export_run_history_catalog(tmp_path: Path) -> None:
    rec_dir = tmp_path / "receipts"
    ledger = tmp_path / "ledger.jsonl"
    for q in ("sharp money", "rizz", "locked in"):
        result = detect_memetic_patterns(query=q, ingest_source="mock")
        emit_receipt(result, out_dir=rec_dir, append_ledger=True, ledger_path=ledger)
    root = tmp_path / "docs_archive"
    meta = export_run_history(
        archive_root=root,
        ledger_path=ledger,
        receipt_dirs=[rec_dir],
        snapshot_id="run-alpha",
        notes="unit test history",
    )
    assert meta["ok"] is True
    assert (root / "runs" / "run-alpha" / "index.json").is_file()
    assert (root / "latest" / "index.json").is_file()
    assert (root / "catalog.json").is_file()
    assert (root / "index.md").is_file()
    cat = json.loads((root / "catalog.json").read_text())
    assert cat["schema"] == "hyperlex.archive_catalog.v1"
    assert cat["n_runs"] >= 1
    assert cat["latest_snapshot_id"] == "run-alpha"

    # second run
    export_run_history(
        archive_root=root,
        ledger_path=ledger,
        receipt_dirs=[rec_dir],
        snapshot_id="run-beta",
    )
    cat2 = rebuild_archive_catalog(root)
    assert cat2["n_runs"] == 2
    assert cat2["latest_snapshot_id"] == "run-beta"


def test_phase5_history_snapshot(tmp_path: Path) -> None:
    sc = run_phase5_scenario("rizz", domain="ai")
    digest = sanitize_phase5_summary(sc)
    assert digest["brier"] is None
    assert digest["publish_safe"] is True
    root = tmp_path / "arch"
    meta = export_run_history(
        archive_root=root,
        snapshot_id="p5-demo",
        phase5_scenario=sc,
    )
    assert meta["run_kind"] == "phase5_scenario"
    assert (root / "runs" / "p5-demo" / "phase5.json").is_file()
    # phase5 does not clobber latest
    assert not (root / "latest").exists() or not list((root / "latest").glob("*"))
