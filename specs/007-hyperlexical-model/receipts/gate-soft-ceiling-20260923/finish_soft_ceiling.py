#!/usr/bin/env python3
"""Finish template under soft_ceiling_tiebreak.

When FAIR < 1.0: classic force-fair strictly-greater + E2 + same n.
When FAIR == 1.0: require broad OBSERVED eval > morph65 baseline + E2.

Copy/adapt per morph: set MORPH, OUT, PRIV, FAIR, FAIR_N, GATE_OWNER,
and BROAD_EVAL path (written by poll after train via eval_broad_observed.py).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/home/morpheus/hlx")
from gate_soft_ceiling_decide import decide  # noqa: E402

FAIR = 1.0
FAIR_N = 164
MORPH = 0  # set per morph
OUT = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph0")
PRIOR = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph65")
MODELS = Path("/home/morpheus/.hyperlex/models")
PRIV = Path("/home/morpheus/hlx-private/p1-spark-morph0-soft-ceiling")
LOCK = PRIV / "GATE_LOCK.json"
GATE_OWNER = os.environ.get("GATE_OWNER", "morph0-soft-ceiling")
E2_SRC = Path("/home/morpheus/hlx/e2-unbind-morph0.json")
BROAD_EVAL = Path("/home/morpheus/hlx/broad-eval-morph0.json")
PRIOR_BROAD_EVAL = Path("/home/morpheus/hlx/broad-eval-prior-morph65.json")
GATE_PIN = Path("/home/morpheus/hlx/GATE_SOFT_CEILING.json")


def main() -> int:
    PRIV.mkdir(parents=True, exist_ok=True)
    receipt = OUT / "train-receipt.json"
    if not receipt.is_file():
        print("NO_RECEIPT", file=sys.stderr)
        return 2
    if not E2_SRC.is_file():
        print("NO_E2", file=sys.stderr)
        return 3
    prior_ok = (PRIOR / "model.safetensors").is_file() or (
        PRIOR / "best" / "model.safetensors"
    ).is_file()
    if not PRIOR.is_dir() or not prior_ok:
        print("PRIOR_MISSING", file=sys.stderr)
        return 4
    if LOCK.is_file():
        existing = json.loads(LOCK.read_text())
        if existing.get("status") == "done":
            print(json.dumps({"already_gated": True, "lock": existing}, indent=2))
            return 0
        owner = existing.get("gate_owner")
        if owner and owner != GATE_OWNER and existing.get("status") == "in_progress":
            print(json.dumps({"blocked_by_other_gate": True, "lock": existing}, indent=2))
            return 5

    LOCK.write_text(
        json.dumps(
            {
                "gate_owner": GATE_OWNER,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "pid": os.getpid(),
                "status": "in_progress",
                "gate": "soft_ceiling_tiebreak",
            },
            indent=2,
        )
        + "\n"
    )

    r = json.loads(receipt.read_text())
    e2 = json.loads(E2_SRC.read_text())
    best_exact = float(r.get("best_unbind_exact") or r["val"]["unbind_exact"])
    best_epoch = r.get("best_epoch") or r.get("val", {}).get("epoch")
    val_n = int(r.get("val", {}).get("n_unbind_eval") or 0)
    e2_pass = (
        bool(e2.get("e2_pass"))
        and float(e2.get("unbind_exact") or 0) == 1.0
        and bool(e2.get("trunk_forward"))
    )

    broad_exact = None
    broad_n = None
    broad = None
    if BROAD_EVAL.is_file():
        broad = json.loads(BROAD_EVAL.read_text())
        broad_exact = float(broad.get("unbind_exact") or 0)
        broad_n = int(broad.get("n_scored") or broad.get("n_unbind_eval") or 0)

    prior_broad_exact = None
    prior_broad_n = None
    prior_broad = None
    if PRIOR_BROAD_EVAL.is_file():
        prior_broad = json.loads(PRIOR_BROAD_EVAL.read_text())
        prior_broad_exact = float(prior_broad.get("unbind_exact") or 0)
        prior_broad_n = int(
            prior_broad.get("n_scored") or prior_broad.get("n_unbind_eval") or 0
        )

    verdict = decide(
        force_fair=FAIR,
        force_fair_n=FAIR_N,
        best_exact=best_exact,
        val_n=val_n,
        e2_pass=e2_pass,
        broad_exact=broad_exact,
        broad_n=broad_n,
        prior_broad_exact=prior_broad_exact,
        prior_broad_n=prior_broad_n,
    )
    promote = bool(verdict["promote"])
    decision = str(verdict["decision"])

    best_link = MODELS / "BEST"
    if promote:
        if best_link.is_symlink() or best_link.exists():
            best_link.unlink()
        best_link.symlink_to(OUT)
        (MODELS / "BEST.path").write_text(str(OUT) + "\n")

    pin = {
        "schema": "hyperlex.hyperlexical.best_pin.v0.1",
        "decision": "PIN_BEST" if promote else decision,
        "seed": f"seed-morph{MORPH}",
        "path": str(OUT),
        "prior_best": "seed-morph65",
        "gate": "soft_ceiling_tiebreak",
        "gate_mode": verdict.get("mode"),
        "prior_unbind_exact": FAIR,
        "fair_val_n": FAIR_N,
        "best_unbind_exact": best_exact,
        "best_epoch": best_epoch,
        "val_best": r.get("val"),
        "val_n_train_receipt": val_n,
        "broad_observed": {
            "exact": broad_exact,
            "n": broad_n,
            "baseline_exact": verdict.get("broad_baseline"),
            "baseline_n": verdict.get("broad_baseline_n"),
            "baseline_src": verdict.get("broad_baseline_src"),
            "prior_exact": prior_broad_exact,
            "prior_n": prior_broad_n,
            "path": str(BROAD_EVAL) if BROAD_EVAL.is_file() else None,
            "prior_path": str(PRIOR_BROAD_EVAL) if PRIOR_BROAD_EVAL.is_file() else None,
        },
        "e2": {
            "e2_pass": e2_pass,
            "unbind_exact": e2.get("unbind_exact"),
            "trunk_forward": e2.get("trunk_forward"),
        },
        "verdict": verdict,
        "name_gate": False,
        "pinned_at": datetime.now(timezone.utc).isoformat(),
        "gate_owner": GATE_OWNER,
        "morph65_preserved": not promote,
        "gate_pin": str(GATE_PIN) if GATE_PIN.is_file() else None,
    }

    if promote:
        (OUT / "pin-promote-best.json").write_text(json.dumps(pin, indent=2) + "\n")
        (PRIV / "pin-promote-best.json").write_text(json.dumps(pin, indent=2) + "\n")
        (PRIV / "PROMOTE_BEST.md").write_text(
            f"# morph{MORPH} PROMOTE BEST (soft_ceiling)\n\n"
            f"mode={verdict.get('mode')} decision={decision}\n"
            f"{verdict.get('reason')}\n"
        )
        (PRIV / "STATUS.txt").write_text("PROMOTE_BEST\n")
    else:
        (OUT / "pin-no-promote.json").write_text(json.dumps(pin, indent=2) + "\n")
        (PRIV / "pin-no-promote.json").write_text(json.dumps(pin, indent=2) + "\n")
        (PRIV / "REJECT_VS_BEST.md").write_text(
            f"# morph{MORPH} REJECT (soft_ceiling)\n\n"
            f"mode={verdict.get('mode')} decision={decision}\n"
            f"{verdict.get('reason')}\nBEST stays morph65.\n"
        )
        (PRIV / "STATUS.txt").write_text(decision + "\n")

    Path(f"/home/morpheus/hlx/pin-morph{MORPH}.json").write_text(
        json.dumps(pin, indent=2) + "\n"
    )
    (PRIV / f"pin-morph{MORPH}.json").write_text(json.dumps(pin, indent=2) + "\n")
    if broad is not None:
        (PRIV / BROAD_EVAL.name).write_text(json.dumps(broad, indent=2) + "\n")
    if prior_broad is not None:
        (PRIV / PRIOR_BROAD_EVAL.name).write_text(json.dumps(prior_broad, indent=2) + "\n")
    if E2_SRC.is_file():
        (PRIV / E2_SRC.name).write_text(E2_SRC.read_text())
    for name in ("train-receipt.json", "best-checkpoint.json", "config-train.json"):
        srcp = OUT / name
        if srcp.is_file():
            (PRIV / name).write_text(srcp.read_text())

    lock_done = {
        "gate_owner": GATE_OWNER,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "status": "done",
        "decision": decision,
        "promote": promote,
        "best_unbind_exact": best_exact,
        "best_epoch": best_epoch,
        "fair_morph65": FAIR,
        "fair_n": FAIR_N,
        "gate": "soft_ceiling_tiebreak",
        "gate_mode": verdict.get("mode"),
        "broad_exact": broad_exact,
        "broad_n": broad_n,
        "e2_pass": e2_pass,
        "surface_ok": verdict.get("surface_ok"),
        "val_n": val_n,
        "reason": verdict.get("reason"),
    }
    LOCK.write_text(json.dumps(lock_done, indent=2) + "\n")
    (OUT / "GATE_LOCK.json").write_text(json.dumps(lock_done, indent=2) + "\n")
    print(json.dumps(lock_done, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
