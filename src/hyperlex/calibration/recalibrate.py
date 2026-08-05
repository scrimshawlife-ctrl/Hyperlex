"""Mean-shift recalibration diagnostics (advisory only).

When yates.bias_squared stays elevated on a cohort, operators may apply a
simple additive shift to future forecast probabilities. This module never
mutates historical forecasts or invents Brier scores.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence


def mean_shift_from_series(series: Dict[str, Any]) -> Dict[str, Any]:
    """
    Derive an advisory mean-shift from a score_series result.

    shift = mean_outcome − mean_forecast  (classical Yates means)
    Apply as: f' = clamp(f + shift, 0, 1) on *future* forecasts only.

    Returns status NOT_COMPUTABLE when series is unscored or means missing.
    """
    if series.get("status") != "SCORED":
        return {
            "status": "NOT_COMPUTABLE",
            "reason": f"series status={series.get('status')}",
            "shift": None,
            "apply": "none",
        }

    yates = series.get("yates") or {}
    mean_f = yates.get("mean_forecast")
    mean_o = yates.get("mean_outcome")
    bias_sq = yates.get("bias_squared")

    if not isinstance(mean_f, (int, float)) or not isinstance(mean_o, (int, float)):
        return {
            "status": "NOT_COMPUTABLE",
            "reason": "missing mean_forecast/mean_outcome",
            "shift": None,
            "apply": "none",
        }

    shift = float(mean_o) - float(mean_f)
    elevated = isinstance(bias_sq, (int, float)) and float(bias_sq) >= 0.01

    return {
        "status": "ADVISORY",
        "shift": round(shift, 6),
        "mean_forecast": float(mean_f),
        "mean_outcome": float(mean_o),
        "bias_squared": bias_sq,
        "elevated_bias": elevated,
        "apply": "future_forecasts_only",
        "formula": "f_prime = clamp(f + shift, 0, 1)",
        "note": "Do not rewrite historical forecasts; mapping_version should bump if adopted.",
    }


def apply_mean_shift(
    probability: float,
    shift: float,
) -> float:
    """Pure clamp of f + shift into [0, 1]."""
    v = float(probability) + float(shift)
    return max(0.0, min(1.0, v))


def apply_mean_shift_batch(
    probabilities: Sequence[float],
    shift: float,
) -> list[float]:
    return [apply_mean_shift(p, shift) for p in probabilities]
