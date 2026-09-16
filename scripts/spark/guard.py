#!/usr/bin/env python3
"""Spark CUDA memory guard for Hyperlexical train launches.

Lives on the Spark host as ``~/hlx/guard.py`` (outside the train container's
edit surface for ``loop.py``). This file is the **canonical template** to sync
there; do not import it from the Hyperlex package.

Intent (shared-box safety, not a leftover):
  ``torch.cuda.set_per_process_memory_fraction`` hard-caps the process so an
  OOM kills the trainer instead of the co-tenant (historically Qwen / ComfyUI
  on the same GB10). Bring-up smoke used ``0.03`` (~3.9 GB of ~130 GB). Morph
  climbs later hardcoded ``0.015`` (~2 GB) while Qwen was resident — that
  over-tight cap stuck in ``run_morph_train.sh`` after the co-tenant left.

Fraction policy on a ~130 GB Spark GB10:
  - ``0.03`` — co-tenant smoke / beside live SGLang (original bring-up).
  - ``0.3``  — exclusive morph train default (~39 GB). ModernBERT last-N does
    not need that much; the headroom avoids allocator thrash under a 2 GB cap
    while still leaving ~90 GB if Qwen returns.
  - ``0.5``–``0.8`` — only with explicit operator approval when the box is
    confirmed exclusive and a larger batch / full-finetune needs it.

Override (wins over argv when set):
  ``HYPERLEX_CUDA_MEM_FRACTION=0.3``

Usage:
  python guard.py 0.03 hyperlexical.train --offline --run
  HYPERLEX_CUDA_MEM_FRACTION=0.3 python guard.py 0.03 hyperlexical.train ...
"""

from __future__ import annotations

import os
import runpy
import sys

import torch


def _resolve_frac(argv_frac: str) -> float:
    env_raw = os.environ.get("HYPERLEX_CUDA_MEM_FRACTION")
    if env_raw is not None and str(env_raw).strip() != "":
        frac = float(env_raw)
        source = "env:HYPERLEX_CUDA_MEM_FRACTION"
    else:
        frac = float(argv_frac)
        source = "argv"
    if not (0.0 < frac <= 1.0):
        raise SystemExit(
            f"[guard] fraction must be in (0, 1], got {frac!r} (via {source})"
        )
    return frac


def main(argv: list[str]) -> None:
    if len(argv) < 3:
        raise SystemExit(
            "usage: guard.py <frac> <module> [args...]\n"
            "  optional override: HYPERLEX_CUDA_MEM_FRACTION"
        )
    frac = _resolve_frac(argv[1])
    mod = argv[2]
    torch.cuda.set_per_process_memory_fraction(frac)
    free, total = torch.cuda.mem_get_info()
    env_set = bool(str(os.environ.get("HYPERLEX_CUDA_MEM_FRACTION") or "").strip())
    print(
        f"[guard] frac={frac} argv={argv[1]} env_override={env_set} "
        f"cap={frac * total / 1e9:.1f}GB free={free / 1e9:.1f}GB "
        f"total={total / 1e9:.1f}GB",
        flush=True,
    )
    sys.argv = [mod] + argv[3:]
    runpy.run_module(mod, run_name="__main__")


if __name__ == "__main__":
    main(sys.argv)
