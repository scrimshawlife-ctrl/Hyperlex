"""Brier atomic + series scoring (Murphy, Yates, BSS, v1.1 diagnostics).

Fail-closed: missing/invalid pairs → NOT_COMPUTABLE.

v1.1 additions
--------------
- Vieira non-negative rearrangement of Yates (variance mismatch, correlation deficit, bias²)
- Discrimination slope Δf = mean(f|o=1) − mean(f|o=0)
- Ferro–Fricker bias-corrected Murphy components (better for small n)
"""

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


def _bin_stats(
    predictions: Sequence[float],
    targets: Sequence[float],
    n_bins: int = 10,
) -> List[Dict[str, float]]:
    """Per-bin means and counts for Murphy / Ferro–Fricker."""
    bins: List[Dict[str, float]] = []
    for i in range(n_bins):
        lower = i / n_bins
        upper = (i + 1) / n_bins
        bin_preds: List[float] = []
        bin_targets: List[float] = []
        for p, t in zip(predictions, targets):
            if lower <= p < upper or (i == n_bins - 1 and p == 1.0):
                bin_preds.append(p)
                bin_targets.append(t)
        if bin_preds:
            bins.append({
                "n": float(len(bin_preds)),
                "mean_pred": sum(bin_preds) / len(bin_preds),
                "mean_target": sum(bin_targets) / len(bin_targets),
            })
    return bins


def murphy_decomposition(
    predictions: Sequence[float],
    targets: Sequence[float],
    *,
    n_bins: int = 10,
) -> Dict[str, float | str]:
    """Standard Murphy REL − RES + UNC (finite-sample biased component estimates)."""
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

    for b in _bin_stats(predictions, targets, n_bins=n_bins):
        weight = b["n"] / n
        reliability += weight * (b["mean_pred"] - b["mean_target"]) ** 2
        resolution += weight * (b["mean_target"] - mean_target) ** 2

    uncertainty = mean_target * (1.0 - mean_target)
    return {
        "reliability": reliability,
        "resolution": resolution,
        "uncertainty": uncertainty,
        "brier_score": reliability - resolution + uncertainty,
    }


def murphy_decomposition_ferro(
    predictions: Sequence[float],
    targets: Sequence[float],
    *,
    n_bins: int = 10,
) -> Dict[str, float | str]:
    """
    Ferro–Fricker (2012) bias-corrected Murphy components.

    Prefer this for small n. Standard Murphy overestimates reliability and
    underestimates uncertainty in finite samples.

    UNC̃ = UNĈ + ȳ(1−ȳ)/(n−1)
    RES̃ = REŜ + ȳ(1−ȳ)/(n−1) − (1/n) Σ [n_k/(n_k−1)] ȳ_k(1−ȳ_k)
    REL̃ = REL̂ − (1/n) Σ [n_k/(n_k−1)] ȳ_k(1−ȳ_k)
    """
    if not predictions or len(predictions) != len(targets):
        return {
            "reliability": NOT_COMPUTABLE,
            "resolution": NOT_COMPUTABLE,
            "uncertainty": NOT_COMPUTABLE,
            "brier_score": NOT_COMPUTABLE,
            "correction": "ferro_fricker",
        }

    n = len(predictions)
    if n < 2:
        # correction terms undefined; fall back to standard
        out = murphy_decomposition(predictions, targets, n_bins=n_bins)
        out["correction"] = "standard_fallback_n_lt_2"
        return out

    mean_target = sum(targets) / n
    unc_hat = mean_target * (1.0 - mean_target)
    rel_hat = 0.0
    res_hat = 0.0
    within_bin_term = 0.0  # (1/n) Σ [n_k/(n_k−1)] ȳ_k(1−ȳ_k)

    for b in _bin_stats(predictions, targets, n_bins=n_bins):
        nk = b["n"]
        yk = b["mean_target"]
        weight = nk / n
        rel_hat += weight * (b["mean_pred"] - yk) ** 2
        res_hat += weight * (yk - mean_target) ** 2
        if nk >= 2:
            within_bin_term += (1.0 / n) * (nk / (nk - 1.0)) * yk * (1.0 - yk)
        # nk == 1: the n_k/(n_k−1) factor is undefined; skip (conservative)

    unc_tilde = unc_hat + unc_hat / (n - 1.0)
    res_tilde = res_hat + unc_hat / (n - 1.0) - within_bin_term
    rel_tilde = rel_hat - within_bin_term

    # numerical floor: components can go slightly negative from sampling
    rel_tilde = max(0.0, rel_tilde)
    res_tilde = max(0.0, res_tilde)
    unc_tilde = max(0.0, unc_tilde)

    return {
        "reliability": rel_tilde,
        "resolution": res_tilde,
        "uncertainty": unc_tilde,
        "brier_score": rel_tilde - res_tilde + unc_tilde,
        "correction": "ferro_fricker",
        "uncorrected": {
            "reliability": rel_hat,
            "resolution": res_hat,
            "uncertainty": unc_hat,
        },
    }


def yates_decomposition(
    predictions: Sequence[float],
    targets: Sequence[float],
) -> Dict[str, float | str]:
    """Classical Yates covariance decomposition."""
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
        "mean_forecast": mean_p,
        "mean_outcome": mean_t,
        "cov_fo": cov,
        "var_f": excess_variance,
        "var_o": outcome_variance,
    }


def yates_vieira(
    predictions: Sequence[float],
    targets: Sequence[float],
) -> Dict[str, float | str]:
    """
    Vieira (2026) non-negative rearrangement of Yates.

    BS = (σ_f − σ_o)² + 2(σ_f σ_o − Cov(f,o)) + (μ_f − μ_o)²

    All three terms ≥ 0. Optimality: match variance, perfect correlation, no mean bias.
    """
    if not predictions or len(predictions) != len(targets):
        return {
            "variance_mismatch": NOT_COMPUTABLE,
            "correlation_deficit": NOT_COMPUTABLE,
            "bias_squared": NOT_COMPUTABLE,
            "brier_score": NOT_COMPUTABLE,
        }

    n = len(predictions)
    mean_p = sum(predictions) / n
    mean_t = sum(targets) / n
    var_f = sum((p - mean_p) ** 2 for p in predictions) / n
    var_o = sum((t - mean_t) ** 2 for t in targets) / n
    cov = sum((p - mean_p) * (t - mean_t) for p, t in zip(predictions, targets)) / n

    sigma_f = var_f ** 0.5
    sigma_o = var_o ** 0.5

    variance_mismatch = (sigma_f - sigma_o) ** 2
    # 2(σ_f σ_o − Cov) ≥ 0 by Cauchy–Schwarz
    correlation_deficit = 2.0 * (sigma_f * sigma_o - cov)
    bias_squared = (mean_p - mean_t) ** 2

    # numerical floor
    correlation_deficit = max(0.0, correlation_deficit)

    return {
        "variance_mismatch": variance_mismatch,
        "correlation_deficit": correlation_deficit,
        "bias_squared": bias_squared,
        "brier_score": variance_mismatch + correlation_deficit + bias_squared,
        "sigma_f": sigma_f,
        "sigma_o": sigma_o,
        "rho": (cov / (sigma_f * sigma_o)) if (sigma_f > 0 and sigma_o > 0) else NOT_COMPUTABLE,
    }


def discrimination_slope(
    predictions: Sequence[float],
    targets: Sequence[float],
) -> Dict[str, float | str]:
    """
    Yates discrimination slope Δf = mean(f | o=1) − mean(f | o=0).

    Higher is better discrimination. Requires at least one positive and one
    negative outcome in the series.
    """
    if not predictions or len(predictions) != len(targets):
        return {
            "delta_f": NOT_COMPUTABLE,
            "mean_f_given_1": NOT_COMPUTABLE,
            "mean_f_given_0": NOT_COMPUTABLE,
            "n_pos": 0,
            "n_neg": 0,
        }

    pos = [p for p, t in zip(predictions, targets) if t == 1.0]
    neg = [p for p, t in zip(predictions, targets) if t == 0.0]

    if not pos or not neg:
        return {
            "delta_f": NOT_COMPUTABLE,
            "mean_f_given_1": (sum(pos) / len(pos)) if pos else NOT_COMPUTABLE,
            "mean_f_given_0": (sum(neg) / len(neg)) if neg else NOT_COMPUTABLE,
            "n_pos": len(pos),
            "n_neg": len(neg),
            "reason": "need both positive and negative outcomes",
        }

    mean_1 = sum(pos) / len(pos)
    mean_0 = sum(neg) / len(neg)
    return {
        "delta_f": mean_1 - mean_0,
        "mean_f_given_1": mean_1,
        "mean_f_given_0": mean_0,
        "n_pos": len(pos),
        "n_neg": len(neg),
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
    n_bins: int = 10,
) -> Dict[str, Any]:
    """
    Aggregate Brier metrics over settled pairs.

    Includes v1.1 diagnostics: Ferro–Fricker Murphy, Vieira Yates, Δf.
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
    empty_murphy = murphy_decomposition([], [])
    empty_yates = yates_decomposition([], [])

    if n == 0:
        return {
            "status": NOT_COMPUTABLE,
            "n": 0,
            "series_brier": NOT_COMPUTABLE,
            "brier_skill_score": NOT_COMPUTABLE,
            "reference": reference,
            "murphy": empty_murphy,
            "murphy_ferro": {**empty_murphy, "correction": "ferro_fricker"},
            "yates": empty_yates,
            "yates_vieira": yates_vieira([], []),
            "discrimination": discrimination_slope([], []),
            "cohort": cohort or {},
        }

    return {
        "status": "SCORED",
        "n": n,
        "series_brier": brier_series(preds, targs),
        "brier_skill_score": brier_skill_score(preds, targs, reference=reference),
        "reference": reference,
        "murphy": murphy_decomposition(preds, targs, n_bins=n_bins),
        "murphy_ferro": murphy_decomposition_ferro(preds, targs, n_bins=n_bins),
        "yates": yates_decomposition(preds, targs),
        "yates_vieira": yates_vieira(preds, targs),
        "discrimination": discrimination_slope(preds, targs),
        "cohort": cohort or {},
    }
