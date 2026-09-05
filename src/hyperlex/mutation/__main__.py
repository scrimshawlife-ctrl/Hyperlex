"""CLI: python -m hyperlex.mutation [text] [--restricted]"""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from .grammar import parse_mutation_trace


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="python -m hyperlex.mutation")
    p.add_argument("text", nargs="+", help="attested civilian text")
    p.add_argument(
        "--restricted",
        action="store_true",
        help="operator-asserted restricted flag (redacts surface)",
    )
    args = p.parse_args(argv)
    text = " ".join(args.text)
    out = parse_mutation_trace(
        text,
        source="cli",
        restricted_intent_suspected=bool(args.restricted),
    )
    print(json.dumps({"ok": True, "command": "mutation-trace", **out}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
