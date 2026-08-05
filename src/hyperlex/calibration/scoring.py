"""Brier atomic + series scoring (Murphy, Yates, BSS). Fail-closed."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

NOT_COMPUTABLE = "NOT_COMPUTABLE"


def brier_atomic(probability: float, outcome_value: float) -> float:
    return (float(probability) - float(outcome_value)) ** 2


def brier_series(predictions: Sequence[float], targets: Sequence[float]) -> float | str:
    if not predictions or len(predictions) != len(targets):
        return NOT_COMPUTABLE
    return sum((p - t) ** 2 for p, t in zip(predictions, targets)) / len(predictions)


def brier_skill_score(
    predictions: Sequence[float],
    targets: Sequence[float],
    *,
    reference: str = "climatology",
) -> float | str:
    bs = brier_series(predictions, targets)
    if bs == NOT_COMPUTABLE or not targets:
        return NOT_COMPUTABLE

    if reference == "climatology":
        mean_t = sum(targets) / len(targets)
        ref_bs = brier_series([mean_t] * len(targets), targets)
    elif reference == "persistence":
        if len(targets) < 2:
            return NOT_COMPUTABLE
        ref_preds = list(targets[:-1]) + [targets[-1]]
        ref_bs = brier_series(ref_preds, targets)
    else:
        return NOT_COMPUTABLE

    if ref_bs == NOT_COMPUTABLE or ref_bs == 0:
        return 0.0 if bs == 0 else NOT_COMPUTABLE
    return 1.0 - (float(bs) / float(ref_bs))


def murphy_decomposition(
    predictions: Sequence[float],
    targets: Sequence[float],
    *,
    n_bins: int = 10,
) -> Dict[str, float | str]:
    if not predictions or len(predictions) != len(targets):
        return {
            "reliability": NOT_COMPUTABLE,
            "resolution": NOT_COMPUTABLE,
            "uncertainty": NOT_COMPUTABLE,
            "brier_score": NOT_COMPUTABLE,
        }

    n = len(predictions)
    mean_target = sum(targets) / n
    reliability = 0.0
    resolution = 0.0

    for i in range(n_bins):
        lower = i / n_bins
        upper = (i + 1) / n_bins
        bin_preds = [p for p, t in zip(predictions, targets) if lower <= p < upper or (i == n_bins - 1 and p == 1.0)]
        bin_targets = [t for p, t in zip(predictions, targets) if lower <= p < upper or (i == n_bins - 1 and p == 1.0)]
        if bin_preds:
            bin_mean_pred = sum(bin_preds) / len(bin_preds)
            bin_mean_target = sum(bin_targets) / len(bin_targets)
            weight = len(bin_preds) / n
            reliability += weight * (bin_mean_pred - bin_mean_target) ** 2
            resolution += weight * (bin_mean_target - mean_target) ** 2

    uncertainty = mean_target * (1.0 - mean_target)
    return {
        "reliability": reliability,
        "resolution": resolution,
        "uncertainty": uncertainty,
        "brier_score": reliability - resolution + uncertainty,
    }


def yates_decomposition(
    predictions: Sequence[float],
    targets: Sequence[float],
) -> Dict[str, float | str]:
    if not predictions or len(predictions) != len(targets):
        return {
            "bias_squared": NOT_COMPUTABLE,
            "excess_variance": NOT_COMPUTABLE,
            "covariance_deficit": NOT_COMPUTABLE,
            "brier_score": NOT_COMPUTABLE,
        }

    n = len(predictions)
    mean_p = sum(predictions) / n
    mean_t = sum(targets) / n
    bias_squared = (mean_p - mean_t) ** 2
    excess_variance = sum((p - mean_p) ** 2 for p in predictions) / n
    outcome_variance = sum((t - mean_t) ** 2 for t in targets) / n
    cov = sum((p - mean_p) * (t - mean_t) for p, t in zip(predictions, targets)) / n
    covariance_deficit = outcome_variance - 2.0 * cov
    return {
        "bias_squared": bias_squared,
        "excess_variance": excess_variance,
        "covariance_deficit": covariance_deficit,
        "brier_score": bias_squared + excess_variance + covariance_deficit,
    }


def score_pair(forecast: Dict[str, Any], settlement: Dict[str, Any]) -> Dict[str, Any]:
    """Atomic score for one forecast–settlement pair."""
    from .settlement import is_scorable

    if not is_scorable(settlement):
        return {
            "status": NOT_COMPUTABLE,
            "reason": f"settlement_decision={settlement.get('settlement_decision')}",
            "forecast_id": forecast.get("forecast_id"),
            "settlement_id": settlement.get("settlement_id"),
        }

    if settlement.get("forecast_id") != forecast.get("forecast_id"):
        return {
            "status": NOT_COMPUTABLE,
            "reason": "forecast_id mismatch",
            "forecast_id": forecast.get("forecast_id"),
            "settlement_id": settlement.get("settlement_id"),
        }

    f = float(forecast["probability"])
    o = float(settlement["outcome_value"])
    return {
        "status": "SCORED",
        "forecast_id": forecast["forecast_id"],
        "settlement_id": settlement["settlement_id"],
        "probability": f,
        "outcome_value": o,
        "atomic_score": brier_atomic(f, o),
        "signal_key": forecast.get("signal_key"),
    }


def score_series(
    pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]],
    *,
    reference: str = "climatology",
    cohort: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Aggregate Brier metrics over settled pairs.

    Only TRUE/FALSE settlements contribute. Empty set → NOT_COMPUTABLE.
    """
    preds: List[float] = []
    targs: List[float] = []

    for forecast, settlement in pairs:
        rec = score_pair(forecast, settlement)
        if rec.get("status") == "SCORED":
            preds.append(float(rec["probability"]))
            targs.append(float(rec["outcome_value"]))

    n = len(preds)
    if n == 0:
        return {
            "status": NOT_COMPUTABLE,
            "n": 0,
            "series_brier": NOT_COMPUTABLE,
            "brier_skill_score": NOT_COMPUTABLE,
            "reference": reference,
            "murphy": murphy_decomposition([], []),
            "yates": yates_decomposition([], []),
            "cohort": cohort or {},
        }

    return {
        "status": "SCORED",
        "n": n,
        "series_brier": brier_series(preds, targs),
        "brier_skill_score": brier_skill_score(preds, targs, reference=reference),
        "reference": reference,
        "murphy": murphy_decomposition(preds, targs),
        "yates": yates_decomposition(preds, targs),
        "cohort": cohort or {},
    }
