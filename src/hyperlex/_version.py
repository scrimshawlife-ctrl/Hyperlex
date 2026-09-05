"""Version resolution that works in a wheel and a git checkout."""
from __future__ import annotations

from pathlib import Path


def read_version() -> str:
    try:
        from importlib.metadata import version as pkg_version

        return pkg_version("hyperlex")
    except Exception:
        pass
    here = Path(__file__).resolve()
    for candidate in (here.parents[2] / "VERSION", here.parent / "VERSION"):
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8").strip() or "0.4.0"
    return "0.4.0"
