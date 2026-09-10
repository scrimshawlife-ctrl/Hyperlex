"""U3 preflight. No Hub. No train."""

from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path

from .export import export_dataset, repo_root

TRUNK = "answerdotai/ModernBERT-base"


def main(argv=None) -> int:
    root = repo_root()
    allow = os.environ.get("HYPERLEX_ALLOW_TRAIN") == "1"
    trunk = Path(os.environ.get("HYPERLEX_TRUNK_DIR") or "")
    bundle = export_dataset(root)
    report = {
        "schema": "hyperlex.hyperlexical.preflight.v0.1",
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "allow_train": allow,
        "trunk_id": TRUNK,
        "trunk_dir": str(trunk) if trunk else None,
        "trunk_dir_exists": trunk.is_dir() if trunk else False,
        "trunk_config": (trunk / "config.json").is_file() if trunk else False,
        "data_sha256": bundle["sha256"],
        "data_counts": bundle["counts"],
        "name_gate": False,
        "brier": None,
        "ready_to_train": bool(
            allow and trunk.is_dir() and (trunk / "config.json").is_file()
        ),
        "note": "ready_to_train is a gate check, not E2 and not a Hyperlexical name.",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["ready_to_train"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
