"""Opt-in training seed (HLX_SEED, default off).

Unset makes no seeding calls. When set, seeds Python ``random``, NumPy, and
PyTorch (CPU and CUDA) and turns on deterministic cuDNN plus
``torch.use_deterministic_algorithms(True)``. ``PYTHONHASHSEED`` is recorded
for child processes; the current process hash seed is fixed at startup.
"""

from __future__ import annotations

import os
import random
from typing import Any

SEED_ENV = "HLX_SEED"
_SEED_MAX = 2**32 - 1


def resolve_training_seed(raw: str | None = None) -> int | None:
    """Return the seed, or None when unset. Non-integers fail closed."""
    if raw is None:
        raw = os.environ.get(SEED_ENV)
    if raw is None:
        return None
    token = str(raw).strip()
    if token == "":
        return None
    if not token.isdigit():
        raise SystemExit(f"REFUSE: {SEED_ENV} must be a non-negative integer")
    value = int(token)
    if value > _SEED_MAX:
        raise SystemExit(f"REFUSE: {SEED_ENV} must be <= {_SEED_MAX}")
    return value


def apply_training_seed(torch_mod: Any = None) -> dict[str, Any] | None:
    """Seed RNGs when ``HLX_SEED`` is set. Unset returns None and touches nothing."""
    seed = resolve_training_seed()
    if seed is None:
        return None
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    import numpy as np

    np.random.seed(seed)
    if torch_mod is None:
        import torch as torch_mod

    torch_mod.manual_seed(seed)
    if torch_mod.cuda.is_available():
        torch_mod.cuda.manual_seed_all(seed)
    torch_mod.backends.cudnn.deterministic = True
    torch_mod.backends.cudnn.benchmark = False
    deterministic = True
    try:
        torch_mod.use_deterministic_algorithms(True)
    except Exception:
        deterministic = False
    return {
        "seed": seed,
        "python_hash_seed": str(seed),
        "numpy": True,
        "deterministic_algorithms": deterministic,
        "cudnn_deterministic": True,
    }
