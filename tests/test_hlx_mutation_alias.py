"""Skill-tree mutation alias."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_hlx_mutation_trace_alias():
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "HYPERLEX_OFFLINE": "1"}
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "hlx-mutation"), "trace", "it's", "giving", "mid", "rizz"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data.get("ok") is True
    assert data.get("brier") is None
    assert data.get("forecast_eligible") is False
    assert "REGISTER_SHIFT" in data.get("operators", []) or "SUBSTITUTE" in data.get("operators", [])
