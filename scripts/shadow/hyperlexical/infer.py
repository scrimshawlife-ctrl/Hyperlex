"""SHADOW CLI. Offline stub. No torch. No Hub."""

from __future__ import annotations

import argparse
import json
import os
import sys

from .packet import build_packet


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="hyperlexical-infer")
    p.add_argument("--text", default="")
    p.add_argument("--offline", action="store_true", default=True)
    p.add_argument("--restricted", action="store_true")
    p.add_argument("--role-scheme", default="positional", choices=("positional", "type_slot"))
    p.add_argument("--out", default="")
    args = p.parse_args(argv)
    if os.environ.get("HYPERLEX_OFFLINE") == "0" and not args.offline:
        print("abort: online infer is out of U1", file=sys.stderr)
        return 2
    packet = build_packet(
        args.text,
        restricted=args.restricted,
        role_scheme=args.role_scheme,
    )
    text = json.dumps(packet, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.write("\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
