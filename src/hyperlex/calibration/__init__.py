"""calibration — Brier / forecast / settlement layer for Hyperlex.

Forecasts are derived from analysis results. Brier scores exist only after
settlement. Unsettled paths return NOT_COMPUTABLE — never a fabricated number.

v1.1 diagnostics: Vieira Yates, Ferro–Fricker Murphy, discrimination slope Δf.
Operator path: score_log (append-only) + settle_and_log + recompute_series.
"""

from .forecast import extract_forecasts
from .settlement import settle, is_scorable
from .scoring import (
    score_pair,
    score_series,
    brier_atomic,
    brier_series,
    brier_skill_score,
    murphy_decomposition,
    murphy_decomposition_ferro,
    yates_decomposition,
    yates_vieira,
    discrimination_slope,
    NOT_COMPUTABLE,
)
from .score_log import (
    default_log_path,
    repo_log_path,
    append_forecast,
    append_settlement,
    append_score,
    settle_and_log,
    read_log,
    load_pairs,
    recompute_series,
    verify_chain,
)
from .export import to_brier_ledger_entry, compute_ledger_hash
from .recalibrate import mean_shift_from_series, apply_mean_shift

__all__ = [
    "extract_forecasts",
    "settle",
    "is_scorable",
    "score_pair",
    "score_series",
    "brier_atomic",
    "brier_series",
    "brier_skill_score",
    "murphy_decomposition",
    "murphy_decomposition_ferro",
    "yates_decomposition",
    "yates_vieira",
    "discrimination_slope",
    "NOT_COMPUTABLE",
    "default_log_path",
    "repo_log_path",
    "append_forecast",
    "append_settlement",
    "append_score",
    "settle_and_log",
    "read_log",
    "load_pairs",
    "recompute_series",
    "verify_chain",
    "to_brier_ledger_entry",
    "compute_ledger_hash",
    "mean_shift_from_series",
    "apply_mean_shift",
]
