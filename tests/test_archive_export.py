"""Sanitized analysis archive export."""

from __future__ import annotations

import json
from pathlib import Path

from hyperlex import detect_memetic_patterns, emit_receipt, export_analysis_archive
from hyperlex.archive import sanitize_receipt_summary


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
