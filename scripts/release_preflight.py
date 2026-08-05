#!/usr/bin/env python3
"""Preflight checks used for local release hygiene."""

from __future__ import annotations

import subprocess
import sys


def run(cmd: str) -> bool:
    proc = subprocess.run(cmd, shell=True)
    return proc.returncode == 0


def main() -> int:
    checks = {
        "check": "python3 scripts/hyperlex.py check",
        "smoke": "python3 scripts/hyperlex.py smoke",
        "tests": "python3 -m pytest -q",
    }
    failed = []
    for name, command in checks.items():
        if not run(command):
            failed.append(name)
    if failed:
        print("preflight failed:", ", ".join(failed))
        return 2
    print("preflight ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
