"""Diagram generation from golden receipts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from hyperlex.diagrams import (
    diagram_from_receipt_files,
    diagram_receipt_flow,
    diagram_lineage_distribution,
    diagram_receipt_timeline,
    write_diagram_bundle,
)
from hyperlex import detect_memetic_patterns, emit_receipt

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "examples" / "receipts" / "golden"
SCRIPT = ROOT / "scripts" / "hyperlex.py"


def test_lineage_distribution_from_golden() -> None:
    paths = sorted(p for p in GOLDEN.glob("*.json") if p.name != "MANIFEST.json")
    assert len(paths) >= 4
    diagrams = diagram_from_receipt_files(paths)
    assert "lineage_distribution" in diagrams
    assert "pie" in diagrams["lineage_distribution"]
    assert "betting-sharp" in diagrams["lineage_distribution"]
    assert "receipt_timeline" in diagrams
    assert "flowchart" in diagrams["receipt_timeline"]
    assert "family_graph" in diagrams
    # per-receipt flows
    flow_keys = [k for k in diagrams if k.startswith("flow_")]
    assert len(flow_keys) >= 4


def test_single_receipt_flow() -> None:
    path = GOLDEN / "betting-sharp.json"
    rec = json.loads(path.read_text(encoding="utf-8"))
    mmd = diagram_receipt_flow(rec)
    assert "flowchart" in mmd
    assert "Lineage" in mmd
    assert "brier=null" in mmd
    assert "Archive" in mmd


def test_write_bundle(tmp_path: Path) -> None:
    paths = list(GOLDEN.glob("betting-sharp.json"))
    diagrams = diagram_from_receipt_files(paths)
    written = write_diagram_bundle(diagrams, tmp_path / "out", html=True, prefix="test")
    assert "lineage_distribution" in written
    mmd = Path(written["lineage_distribution"])
    assert mmd.exists()
    assert "```mermaid" in mmd.read_text(encoding="utf-8")
    assert Path(written["lineage_distribution_html"]).exists()


def test_empty_timeline() -> None:
    mmd = diagram_receipt_timeline([])
    assert "No receipts" in mmd


def test_cli_diagram_from_golden(tmp_path: Path) -> None:
    env = __import__("os").environ.copy()
    env["HYPERLEX_OFFLINE"] = "1"
    out = tmp_path / "diagrams"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "diagram",
            "--from-golden",
            "--out-dir",
            str(out),
            "--prefix",
            "g",
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    body = json.loads(r.stdout)
    assert body["ok"] is True
    assert body["n_diagrams"] >= 3
    assert out.exists()
    assert any(out.glob("*.mmd"))
