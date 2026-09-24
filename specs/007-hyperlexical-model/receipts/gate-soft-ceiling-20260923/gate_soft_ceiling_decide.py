#!/usr/bin/env python3
"""Shared soft_ceiling_tiebreak promote decision.

When force_fair < 1.0: classic force-fair strictly greater + same n + E2.
When force_fair == 1.0: ceiling escape — candidate broad OBSERVED exact must
strictly beat PRIOR (morph65) broad OBSERVED on the same live surface (same n) + E2.

Authorize-time pin (0.889763779527559 n=254) is historical; live SoT can move
(e.g. morph77 val-settle grew OBSERVED val). Prefer prior_broad_* from a fresh
eval of BEST on current SoT; fall back to pin only if prior eval absent.
"""
from __future__ import annotations

from typing import Any


# Historical pin at authorize (pre morph77 settle surface). Prefer live prior.
PIN_BROAD_EXACT = 0.889763779527559
PIN_BROAD_N = 254


def decide(
    *,
    force_fair: float,
    force_fair_n: int,
    best_exact: float,
    val_n: int,
    e2_pass: bool,
    broad_exact: float | None = None,
    broad_n: int | None = None,
    prior_broad_exact: float | None = None,
    prior_broad_n: int | None = None,
) -> dict[str, Any]:
    """Return promote decision under soft_ceiling_tiebreak."""
    ceiling = float(force_fair) >= 1.0 - 1e-12
    if not ceiling:
        surface_ok = int(val_n) == int(force_fair_n)
        promote = bool(best_exact > force_fair and e2_pass and surface_ok)
        if not surface_ok:
            decision = "REJECT_SURFACE"
        else:
            decision = "PROMOTE_BEST" if promote else "REJECT_VS_BEST"
        return {
            "gate": "soft_ceiling_tiebreak",
            "mode": "force_fair",
            "promote": promote,
            "decision": decision,
            "surface_ok": surface_ok,
            "force_fair": force_fair,
            "force_fair_n": force_fair_n,
            "best_exact": best_exact,
            "val_n": val_n,
            "e2_pass": e2_pass,
            "broad_exact": broad_exact,
            "broad_n": broad_n,
            "prior_broad_exact": prior_broad_exact,
            "prior_broad_n": prior_broad_n,
            "reason": (
                f"force_fair mode: best {best_exact} > fair {force_fair} "
                f"n={force_fair_n} + E2"
            ),
        }

    if broad_exact is None or broad_n is None:
        return {
            "gate": "soft_ceiling_tiebreak",
            "mode": "ceiling_escape",
            "promote": False,
            "decision": "REJECT_NO_BROAD_EVAL",
            "surface_ok": False,
            "force_fair": force_fair,
            "force_fair_n": force_fair_n,
            "best_exact": best_exact,
            "val_n": val_n,
            "e2_pass": e2_pass,
            "broad_exact": broad_exact,
            "broad_n": broad_n,
            "prior_broad_exact": prior_broad_exact,
            "prior_broad_n": prior_broad_n,
            "reason": "force_fair==1.0 but candidate broad OBSERVED eval missing",
        }

    # Live prior preferred; else historical pin
    if prior_broad_exact is not None and prior_broad_n is not None:
        baseline_exact = float(prior_broad_exact)
        baseline_n = int(prior_broad_n)
        baseline_src = "live_prior_broad"
    else:
        baseline_exact = PIN_BROAD_EXACT
        baseline_n = PIN_BROAD_N
        baseline_src = "authorize_pin"

    surface_ok = int(broad_n) == int(baseline_n)
    promote = bool(float(broad_exact) > baseline_exact and e2_pass and surface_ok)
    if not surface_ok:
        decision = "REJECT_BROAD_SURFACE"
    else:
        decision = "PROMOTE_BEST" if promote else "REJECT_VS_BROAD_BASELINE"
    return {
        "gate": "soft_ceiling_tiebreak",
        "mode": "ceiling_escape",
        "promote": promote,
        "decision": decision,
        "surface_ok": surface_ok,
        "force_fair": force_fair,
        "force_fair_n": force_fair_n,
        "best_exact": best_exact,
        "val_n": val_n,
        "e2_pass": e2_pass,
        "broad_exact": broad_exact,
        "broad_n": broad_n,
        "prior_broad_exact": prior_broad_exact,
        "prior_broad_n": prior_broad_n,
        "broad_baseline": baseline_exact,
        "broad_baseline_n": baseline_n,
        "broad_baseline_src": baseline_src,
        "authorize_pin_exact": PIN_BROAD_EXACT,
        "authorize_pin_n": PIN_BROAD_N,
        "reason": (
            f"ceiling escape: broad {broad_exact} > baseline {baseline_exact} "
            f"(src={baseline_src}) n={baseline_n} + E2 "
            f"(force_fair={force_fair} advisory)"
        ),
    }


if __name__ == "__main__":
    import json
    import sys

    payload = json.loads(sys.stdin.read() or "{}")
    print(json.dumps(decide(**payload), indent=2))
