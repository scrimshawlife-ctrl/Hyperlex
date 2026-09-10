"""U3 train gate + optional --run loop. No Hub."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

TRUNK = "answerdotai/ModernBERT-base"


def _gate() -> tuple[int, dict, Path | None]:
    allow = os.environ.get("HYPERLEX_ALLOW_TRAIN") == "1"
    trunk_dir = os.environ.get("HYPERLEX_TRUNK_DIR", "")
    local = Path(trunk_dir) if trunk_dir else None
    ok = bool(allow and local is not None and local.is_dir() and (local / "config.json").is_file())
    payload = {
        "abort": not ok,
        "trunk": TRUNK,
        "trunk_dir": str(local) if local else None,
        "allow_train": allow,
        "recipe": "specs/007-hyperlexical-model/AARON-SPARK-TRAIN.md",
        "brier": None,
    }
    if not ok:
        payload["reason"] = "set HYPERLEX_ALLOW_TRAIN=1 and HYPERLEX_TRUNK_DIR to a local ModernBERT-base snapshot"
        return 2, payload, None
    return 0, payload, local


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="hyperlexical-train")
    p.add_argument("--offline", action="store_true", default=True)
    p.add_argument("--run", action="store_true", help="execute loop after gate")
    args = p.parse_args(argv)
    code, payload, local = _gate()
    payload["offline"] = bool(args.offline)
    if code != 0:
        print(json.dumps(payload, indent=2), file=sys.stderr)
        return code
    if not args.run:
        payload["note"] = "gate open. pass --run on Spark to execute the seed loop."
        print(json.dumps(payload, indent=2))
        return 0
    from .loop import run_loop

    out = Path(os.environ.get("HYPERLEX_TRAIN_OUT") or (Path.home() / ".hyperlex" / "models" / "hyperlex-encoder-modernbert-base-seed"))
    try:
        receipt = run_loop(local, out)
    except Exception as exc:
        print(json.dumps({"abort": True, "error": str(exc), "brier": None}, indent=2), file=sys.stderr)
        return 4
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
