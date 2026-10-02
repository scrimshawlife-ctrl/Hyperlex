"""python -m hyperlex.instrument — observe CLI / API launcher."""

from __future__ import annotations

import argparse
import json
import sys

from .api import main as api_main
from .runtime import get_capabilities, get_manifest, health, observe


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    p = argparse.ArgumentParser(prog="python -m hyperlex.instrument")
    sub = p.add_subparsers(dest="cmd", required=True)

    o = sub.add_parser("observe", help="observe text → HyperlexObservation")
    o.add_argument("text")
    o.add_argument(
        "--requested",
        nargs="*",
        default=None,
        help="evidence representation candidates neighborhood diagnostics",
    )

    sub.add_parser("health")
    sub.add_parser("manifest")
    sub.add_parser("capabilities")

    a = sub.add_parser("serve", help="start minimal HTTP API")
    a.add_argument("--host", default="127.0.0.1")
    a.add_argument("--port", type=int, default=8741)

    args = p.parse_args(argv)
    if args.cmd == "observe":
        print(json.dumps(observe(args.text, requested=args.requested), indent=2))
        return 0
    if args.cmd == "health":
        print(json.dumps(health(), indent=2))
        return 0
    if args.cmd == "manifest":
        print(json.dumps(get_manifest(), indent=2))
        return 0
    if args.cmd == "capabilities":
        print(json.dumps(get_capabilities(), indent=2))
        return 0
    if args.cmd == "serve":
        return api_main(["--host", args.host, "--port", str(args.port)])
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
