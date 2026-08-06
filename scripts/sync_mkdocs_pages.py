#!/usr/bin/env python3
"""Rewrite root-doc copies under docs/ so MkDocs --strict link checks pass."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

# (file under docs/, list of (old, new) replacements)
FIXES = {
    "design-orchestra.md": [
        ("](../ROADMAP.md)", "](ROADMAP.md)"),
        ("](../SPEC.md)", "](spec.md)"),
        ("](../ARCHITECTURE.md)", "](architecture.md)"),
    ],

    "architecture.md": [
        ("](./SPEC.md)", "](spec.md)"),
        ("](./docs/api-v1.md)", "](api-v1.md)"),
        ("](./docs/hermes-skill.md)", "](hermes-skill.md)"),
        ("](./ARCHITECTURE.md)", "](architecture.md)"),
        ("](./DESIGN.md)", "](design.md)"),
    ],
    "design.md": [
        ("](../SPEC.md)", "](spec.md)"),
        ("](../ARCHITECTURE.md)", "](architecture.md)"),
        ("](./SPEC.md)", "](spec.md)"),
        ("](./ARCHITECTURE.md)", "](architecture.md)"),
        ("](docs/hermes-skill.md)", "](hermes-skill.md)"),
        ("](./docs/hermes-skill.md)", "](hermes-skill.md)"),
        ("](docs/standalone-app.md)", "](hermes-skill.md)"),
    ],
    "spec.md": [
        ("](docs/api-v1.md)", "](api-v1.md)"),
        ("](./docs/api-v1.md)", "](api-v1.md)"),
        ("](docs/brier-calibration.md)", "](brier-calibration.md)"),
    ],
    # STATUS.md is mirrored as docs/status.md; root paths need MkDocs-relative rewrite
    "status.md": [
        (
            "[docs/operator-loop.md](docs/operator-loop.md)",
            "[operator-loop.md](operator-loop.md)",
        ),
        (
            "[docs/demos/atomic-terms.md](docs/demos/atomic-terms.md)",
            "[demos/atomic-terms.md](demos/atomic-terms.md)",
        ),
    ],
    "ROADMAP.md": [
        ("](../ROADMAP.md)", "](https://github.com/scrimshawlife-ctrl/Hyperlex-Hermes-Specs/blob/main/ROADMAP.md)"),
    ],
    "README.md": [
        ("](../ROADMAP.md)", "](ROADMAP.md)"),
        ("](../ARCHITECTURE.md)", "](architecture.md)"),
        ("](../DESIGN.md)", "](design.md)"),
        ("](../SPEC.md)", "](spec.md)"),
        ("](./standalone-app.md)", "](hermes-skill.md)"),
    ],
}


def main() -> None:
    for name, pairs in FIXES.items():
        path = DOCS / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for old, new in pairs:
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")
        print(f"patched {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
