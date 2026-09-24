"""SHADOW CLI. Offline stub by default. ``--model-dir`` runs a local trained checkpoint. No Hub."""

from __future__ import annotations

import argparse
import json
import os
import sys

from .packet import build_packet


def _temperature(path: str) -> float:
    if not path:
        return 1.0
    with open(path, encoding="utf-8") as fh:
        return float(json.load(fh)["all"]["temperature"])


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="hyperlexical-infer")
    p.add_argument("--text", default="")
    p.add_argument("--offline", action="store_true", default=True)
    p.add_argument("--restricted", action="store_true")
    p.add_argument("--role-scheme", default="positional", choices=("positional", "type_slot"))
    p.add_argument("--out", default="")
    p.add_argument("--model-dir", default="", help="local train-out dir (e.g. ~/.hyperlex/models/BEST); needs torch + trunk")
    p.add_argument("--trunk-dir", default="", help="local ModernBERT-base snapshot (default HYPERLEX_TRUNK_DIR)")
    p.add_argument("--calibration", default="", help="calibrate_classify.py JSON; applies its lineage temperature")
    args = p.parse_args(argv)
    if os.environ.get("HYPERLEX_OFFLINE") == "0" and not args.offline:
        print("abort: online infer is out of U1", file=sys.stderr)
        return 2
    if args.model_dir:
        if args.role_scheme != "positional":
            print("abort: trained infer supports role_scheme=positional only", file=sys.stderr)
            return 2
        from .infer_model import InferModelError, infer

        try:
            packet = infer(
                args.text,
                model_dir=args.model_dir,
                trunk_dir=args.trunk_dir or None,
                restricted=args.restricted,
                temperature=_temperature(args.calibration),
            )
        except InferModelError as exc:
            print(json.dumps({"abort": True, "error": str(exc), "brier": None}), file=sys.stderr)
            return 2
    else:
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
