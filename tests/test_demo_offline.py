"""Offline first-success demo path — drives shipped CLI entry point."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_demo_cli_offline_first_success(tmp_path: Path):
    out_dir = tmp_path / "demo-out"
    env = {
        **dict(os.environ),
        "PYTHONPATH": str(ROOT / "src"),
        "HYPERLEX_OFFLINE": "1",
        "HYPERLEX_VECTOR": "0",
    }
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "hyperlex.py"),
            "demo",
            "--query",
            "rizz",
            "--out-dir",
            str(out_dir),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data["ok"] is True
    assert data["command"] == "demo"
    assert data["brier"] is None
    assert data.get("provenance_brier") is None
    assert data.get("receipt")
    assert Path(data["receipt"]).is_file()
    # known atom should match a lineage family offline
    assert data.get("lineage_family") == "brainrot-aura"
    assert data.get("n_atoms") == 1

    receipt = json.loads(Path(data["receipt"]).read_text(encoding="utf-8"))
    assert receipt.get("provenance", {}).get("brier") is None
    assert (receipt.get("analysis") or {}).get("lineage", {}).get("family_id") == "brainrot-aura"


def test_committed_quickstart_sample_has_null_brier():
    summary = ROOT / "examples" / "quickstart" / "demo_summary.json"
    receipt = ROOT / "examples" / "quickstart" / "sample_receipt.json"
    assert summary.is_file(), "commit examples/quickstart/demo_summary.json"
    assert receipt.is_file(), "commit examples/quickstart/sample_receipt.json"
    s = json.loads(summary.read_text(encoding="utf-8"))
    assert s.get("brier") is None
    assert s.get("ok") is True
    r = json.loads(receipt.read_text(encoding="utf-8"))
    assert r.get("provenance", {}).get("brier") is None
