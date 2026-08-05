#!/usr/bin/env python3
"""Preflight checks for Hyperlex Hermes skill release hygiene."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], env: dict | None = None) -> bool:
    full_env = os.environ.copy()
    full_env["HYPERLEX_OFFLINE"] = "1"
    full_env["HYPERLEX_NO_RATE_LIMIT"] = "1"
    full_env["PYTHONPATH"] = str(ROOT / "src")
    if env:
        full_env.update(env)
    proc = subprocess.run(cmd, cwd=ROOT, env=full_env)
    return proc.returncode == 0


def main() -> int:
    py = sys.executable
    checks = {
        "doctor": [py, "scripts/hyperlex.py", "doctor"],
        "check": [py, "scripts/hyperlex.py", "check"],
        "smoke": [py, "scripts/hyperlex.py", "smoke"],
        "diagram": [py, "scripts/hyperlex.py", "diagram", "--from-golden", "--out-dir", "out/preflight-diagrams", "--no-html"],
        "case_study": [py, "scripts/run_case_study.py", "--out-dir", "out/preflight-case"],
        "tests": [py, "-m", "pytest", "-q"],
    }
    failed = []
    for name, command in checks.items():
        print(f"==> {name}: {' '.join(command)}")
        if not run(command):
            failed.append(name)
    if failed:
        print("preflight failed:", ", ".join(failed))
        return 2
    print("preflight ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
