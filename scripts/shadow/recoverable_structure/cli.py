"""Optional CLI. No network flags."""

from __future__ import annotations

import argparse
import sys

from .fit import Abort, run_probe
from .fixtures import snapshot
from .receipt import dumps
from .schemes import ALLOWED_SCHEMES


def main(argv=None):
    p = argparse.ArgumentParser(prog="recoverable-structure-probe")
    p.add_argument("--fixture", choices=("tpr", "atomic_pair"), default="tpr")
    p.add_argument("--schemes", default="positional,type_slot")
    p.add_argument("--selection-proxy", default="unspecified", choices=("weakness", "mdl", "unspecified"))
    p.add_argument("--out", default="")
    p.add_argument("--human", action="store_true")
    args = p.parse_args(argv)
    schemes = [s.strip() for s in args.schemes.split(",") if s.strip()]
    bad = [s for s in schemes if s not in ALLOWED_SCHEMES]
    if bad:
        print(f"abort: forbidden scheme {bad}", file=sys.stderr)
        return 2
    try:
        snap = snapshot(args.fixture)
        result = run_probe(snap, schemes=schemes, selection_proxy=args.selection_proxy)
    except Abort as exc:
        print(f"abort: {exc}", file=sys.stderr)
        return 2
    text = result["card"] if args.human else dumps(result["receipt"])
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.write("\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
