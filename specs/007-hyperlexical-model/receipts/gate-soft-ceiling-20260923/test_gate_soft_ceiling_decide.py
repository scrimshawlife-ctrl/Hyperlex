#!/usr/bin/env python3
"""Unit checks for soft_ceiling decide (no GPU)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate_soft_ceiling_decide import PIN_BROAD_EXACT, decide


def main() -> int:
    d = decide(
        force_fair=0.9,
        force_fair_n=164,
        best_exact=0.95,
        val_n=164,
        e2_pass=True,
    )
    assert d["promote"] and d["mode"] == "force_fair", d

    d = decide(
        force_fair=0.95,
        force_fair_n=164,
        best_exact=0.95,
        val_n=164,
        e2_pass=True,
    )
    assert not d["promote"] and d["decision"] == "REJECT_VS_BEST", d

    d = decide(
        force_fair=1.0,
        force_fair_n=164,
        best_exact=1.0,
        val_n=164,
        e2_pass=True,
    )
    assert not d["promote"] and d["decision"] == "REJECT_NO_BROAD_EVAL", d

    # live prior (post-settle surface)
    d = decide(
        force_fair=1.0,
        force_fair_n=164,
        best_exact=1.0,
        val_n=164,
        e2_pass=True,
        broad_exact=0.90,
        broad_n=256,
        prior_broad_exact=0.88671875,
        prior_broad_n=256,
    )
    assert d["promote"] and d["broad_baseline_src"] == "live_prior_broad", d

    # equal live prior → reject
    d = decide(
        force_fair=1.0,
        force_fair_n=164,
        best_exact=1.0,
        val_n=164,
        e2_pass=True,
        broad_exact=0.88671875,
        broad_n=256,
        prior_broad_exact=0.88671875,
        prior_broad_n=256,
    )
    assert not d["promote"] and d["decision"] == "REJECT_VS_BROAD_BASELINE", d

    # fallback to authorize pin when no live prior
    d = decide(
        force_fair=1.0,
        force_fair_n=164,
        best_exact=1.0,
        val_n=164,
        e2_pass=True,
        broad_exact=PIN_BROAD_EXACT + 0.01,
        broad_n=254,
    )
    assert d["promote"] and d["broad_baseline_src"] == "authorize_pin", d

    d = decide(
        force_fair=1.0,
        force_fair_n=164,
        best_exact=1.0,
        val_n=164,
        e2_pass=True,
        broad_exact=0.99,
        broad_n=250,
        prior_broad_exact=0.88,
        prior_broad_n=256,
    )
    assert not d["promote"] and d["decision"] == "REJECT_BROAD_SURFACE", d

    d = decide(
        force_fair=1.0,
        force_fair_n=164,
        best_exact=1.0,
        val_n=164,
        e2_pass=False,
        broad_exact=0.99,
        broad_n=256,
        prior_broad_exact=0.88,
        prior_broad_n=256,
    )
    assert not d["promote"], d

    print("OK soft_ceiling decide selfcheck")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
