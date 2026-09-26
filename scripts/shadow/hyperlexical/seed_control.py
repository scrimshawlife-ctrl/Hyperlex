"""Opt-in training seed (HLX_SEED, default off).

Unset makes no seeding calls. When set, seeds Python ``random``, NumPy, and
PyTorch (CPU and CUDA) and turns on deterministic cuDNN plus
``torch.use_deterministic_algorithms(True)``. CUDA 10.2 and newer also need
``CUBLAS_WORKSPACE_CONFIG`` of ``:4096:8`` or ``:16:8`` before the CUDA context
exists, or the first deterministic GEMM raises. Unset leaves that variable
alone. When the seed is set and the variable is empty, this module sets
``:4096:8`` before any CUDA call. ``PYTHONHASHSEED`` is recorded for child
processes; the current process hash seed is fixed at startup.
"""

from __future__ import annotations

import importlib
import os
import random
from typing import Any

SEED_ENV = "HLX_SEED"
CUBLAS_WORKSPACE_ENV = "CUBLAS_WORKSPACE_CONFIG"
_CUBLAS_CHOICES = (":4096:8", ":16:8")
_CUBLAS_DEFAULT = ":4096:8"
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


def _cublas_workspace(raw: str | None = None) -> str | None:
    if raw is None:
        raw = os.environ.get(CUBLAS_WORKSPACE_ENV)
    if raw is None:
        return None
    token = str(raw).strip()
    return token or None


def _cuda_initialized(torch_mod: Any) -> bool:
    try:
        return bool(torch_mod.cuda.is_initialized())
    except Exception:
        return False


def ensure_cublas_workspace(torch_mod: Any = None) -> str:
    """Return a supported cuBLAS workspace. Empty becomes ``:4096:8``.

    Must run before the CUDA context exists unless the variable was already
    a supported value. An unsupported value fails closed.
    """
    current = _cublas_workspace()
    if torch_mod is not None and _cuda_initialized(torch_mod) and current not in _CUBLAS_CHOICES:
        raise SystemExit(
            f"REFUSE: {CUBLAS_WORKSPACE_ENV} must be {_CUBLAS_CHOICES[0]} or "
            f"{_CUBLAS_CHOICES[1]} before CUDA init when {SEED_ENV} is set"
        )
    if current is None:
        os.environ[CUBLAS_WORKSPACE_ENV] = _CUBLAS_DEFAULT
        return _CUBLAS_DEFAULT
    if current not in _CUBLAS_CHOICES:
        raise SystemExit(
            f"REFUSE: {CUBLAS_WORKSPACE_ENV} must be {_CUBLAS_CHOICES[0]} or "
            f"{_CUBLAS_CHOICES[1]} when {SEED_ENV} is set"
        )
    os.environ[CUBLAS_WORKSPACE_ENV] = current
    return current


def apply_training_seed(torch_mod: Any = None) -> dict[str, Any] | None:
    """Seed RNGs when ``HLX_SEED`` is set. Unset returns None and touches nothing."""
    seed = resolve_training_seed()
    if seed is None:
        return None
    prior = _cublas_workspace()
    if torch_mod is None:
        torch_mod = importlib.import_module("torch")
    if _cuda_initialized(torch_mod) and prior not in _CUBLAS_CHOICES:
        raise SystemExit(
            f"REFUSE: {CUBLAS_WORKSPACE_ENV} must be {_CUBLAS_CHOICES[0]} or "
            f"{_CUBLAS_CHOICES[1]} before CUDA init when {SEED_ENV} is set"
        )
    workspace = ensure_cublas_workspace(torch_mod)
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    import numpy as np

    np.random.seed(seed)
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
        "cublas_workspace_config": workspace,
    }
