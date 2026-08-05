"""calibration — Brier / forecast / settlement layer for Hyperlex.

Forecasts are derived from analysis results. Brier scores exist only after
settlement. Unsettled paths return NOT_COMPUTABLE — never a fabricated number.
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
    yates_decomposition,
    NOT_COMPUTABLE,
)

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
    "yates_decomposition",
    "NOT_COMPUTABLE",
]
