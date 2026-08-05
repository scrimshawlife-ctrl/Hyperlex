"""Doctor command health check."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "hyperlex.py"


def test_doctor_ok() -> None:
    env = os.environ.copy()
    env["HYPERLEX_OFFLINE"] = "1"
    env["HYPERLEX_NO_RATE_LIMIT"] = "1"
    env["PYTHONPATH"] = str(ROOT / "src")
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "doctor"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    body = json.loads(r.stdout)
    assert body["ok"] is True
    assert body["command"] == "doctor"
    assert body["posture"] == "hermes_skill_python_package_repo"
    assert body["n_failed"] == 0
    names = {c["name"] for c in body["checks"]}
    assert "brier_null" in names
    assert "api_v1" in names
    assert "golden_corpus" in names
