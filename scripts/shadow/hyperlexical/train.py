"""U3 train gate. Refuses unless operator flag + local trunk. No Hub."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

TRUNK = "answerdotai/ModernBERT-base"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="hyperlexical-train")
    p.add_argument("--offline", action="store_true", default=True)
    args = p.parse_args(argv)
    allow = os.environ.get("HYPERLEX_ALLOW_TRAIN") == "1"
    trunk_dir = os.environ.get("HYPERLEX_TRUNK_DIR", "")
    local = Path(trunk_dir) if trunk_dir else None
    if not allow or local is None or not local.is_dir():
        print(
            json.dumps(
                {
                    "abort": True,
                    "reason": "train gated: set HYPERLEX_ALLOW_TRAIN=1 and HYPERLEX_TRUNK_DIR to a local ModernBERT-base snapshot",
                    "trunk": TRUNK,
                    "recipe": "specs/007-hyperlexical-model/u3-recipe.md",
                    "brier": None,
                    "offline": bool(args.offline),
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2
    print(
        json.dumps(
            {
                "abort": False,
                "note": "Local trunk present. Full SFT loop is still operator-owned on Spark; this gate only unlocks the path.",
                "trunk_dir": str(local),
                "brier": None,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
