#!/usr/bin/env python3
"""soft_ceiling finish: read receipts, decide, write verdict. No torch.

Canonical replacement for ``~/hlx/finish_soft_ceiling.py`` (archived). The
decision uses the **clean** slice of ``eval_broad.py`` output for candidate and
prior, and fails closed on overlap. ``BEST`` moves only with ``--apply-best``.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "shadow"))

from hyperlexical.soft_ceiling import decide  # noqa: E402


def _load(path: str | None) -> dict | None:
    return json.loads(Path(path).read_text()) if path else None


def build_verdict(*, receipt: dict, e2: dict, fair: dict, broad: dict | None, prior_broad: dict | None, slice_name: str) -> dict:
    val = receipt.get("val_best") or receipt.get("val") or {}
    e2_pass = bool(e2.get("e2_pass")) and float(e2.get("unbind_exact") or 0) == 1.0 and bool(e2.get("trunk_forward"))
    cand = (broad or {}).get("slices", {}).get(slice_name) if broad else None
    prior = (prior_broad or {}).get("slices", {}).get(slice_name) if prior_broad else None
    return decide(
        force_fair=float(fair.get("fair_exact", fair.get("unbind_exact"))),
        force_fair_n=int(fair.get("fair_n", fair.get("n_scored"))),
        best_exact=float(receipt.get("best_unbind_exact") or val.get("unbind_exact") or 0),
        val_n=int(val.get("n_unbind_eval") or 0),
        e2_pass=e2_pass,
        broad_exact=None if not cand else cand.get("unbind_exact"),
        broad_n=None if not cand else cand.get("n_scored"),
        prior_broad_exact=None if not prior else prior.get("unbind_exact"),
        prior_broad_n=None if not prior else prior.get("n_scored"),
        broad_overlap=None if not cand else cand.get("overlap"),
    )


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--candidate", required=True, help="candidate train-out dir")
    p.add_argument("--e2", required=True)
    p.add_argument("--fair", required=True)
    p.add_argument("--broad", required=True, help="eval_broad.py output for candidate")
    p.add_argument("--prior-broad", required=True, help="eval_broad.py output for prior BEST")
    p.add_argument("--slice", default="clean", choices=("clean", "oov"))
    p.add_argument("--out", required=True)
    p.add_argument("--apply-best", action="store_true", help="re-point models/BEST on PROMOTE_BEST")
    args = p.parse_args(argv)

    cand = Path(args.candidate)
    receipt = json.loads((cand / "train-receipt.json").read_text())
    verdict = build_verdict(
        receipt=receipt,
        e2=_load(args.e2),
        fair=_load(args.fair),
        broad=_load(args.broad),
        prior_broad=_load(args.prior_broad),
        slice_name=args.slice,
    )
    verdict.update(
        {
            "schema": "hyperlex.soft_ceiling_verdict.v0.2",
            "as_of": datetime.now(timezone.utc).isoformat(),
            "candidate": str(cand),
            "slice": args.slice,
            "applied_best": False,
            "name_gate": False,
        }
    )
    if verdict["promote"] and args.apply_best:
        best = cand.parent / "BEST"
        if best.is_symlink() or best.exists():
            best.unlink()
        best.symlink_to(cand)
        (cand.parent / "BEST.path").write_text(str(cand) + "\n")
        verdict["applied_best"] = True
    Path(args.out).write_text(json.dumps(verdict, indent=2) + "\n")
    print(json.dumps({k: verdict[k] for k in ("decision", "promote", "reason", "applied_best")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
