"""Advisory transmission parameter calibration from settled pairs.

Uses settled forecast series (golden fixture or score log pairs) as *targets*
for a coarse grid over (beta, gamma). Results are SPECULATIVE research hints
for future simulations — they do **not** invent Brier scores and do not rewrite
settlements.

Mapping:
  - Prefer pairs with signal_key containing virality / hyperstition / lineage
  - target = outcome_value in {0,1}
  - sim feature = peak_mean_adoption under candidate (beta, gamma)
  - loss = mean absolute error between peak and outcome
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .transmission import simulate_cultural_transmission


def _pairs_from_golden(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for row in data.get("pairs") or []:
        if not isinstance(row, dict):
            continue
        fc = row.get("forecast") or {}
        st = row.get("settlement") or {}
        if str(st.get("settlement_decision") or "").upper() in {"VOID", "CONFLICT"}:
            continue
        if "outcome_value" not in st:
            continue
        out.append({
            "forecast_id": fc.get("forecast_id"),
            "signal_key": fc.get("signal_key"),
            "probability": fc.get("probability"),
            "outcome_value": float(st["outcome_value"]),
            "seed_term": str(fc.get("target_event") or fc.get("signal_key") or "signal"),
            "virality_hybrid": float(fc.get("probability") or 0.5),
        })
    return out


def _pairs_from_series(series: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Accept score_series-like dict with pairs or atomic scores."""
    out = []
    for row in series.get("pairs") or series.get("scored_pairs") or []:
        if not isinstance(row, dict):
            continue
        fc = row.get("forecast") or row
        st = row.get("settlement") or {}
        ov = st.get("outcome_value", row.get("outcome_value"))
        if ov is None:
            continue
        out.append({
            "forecast_id": fc.get("forecast_id") or row.get("forecast_id"),
            "signal_key": fc.get("signal_key") or row.get("signal_key"),
            "probability": fc.get("probability") or row.get("probability"),
            "outcome_value": float(ov),
            "seed_term": str(fc.get("signal_key") or "signal"),
            "virality_hybrid": float(fc.get("probability") or row.get("probability") or 0.5),
        })
    return out


def load_calibration_pairs(
    *,
    golden_path: Optional[Path | str] = None,
    series: Optional[Dict[str, Any]] = None,
    signal_key_contains: Optional[str] = None,
) -> List[Dict[str, Any]]:
    pairs: List[Dict[str, Any]] = []
    if series:
        pairs.extend(_pairs_from_series(series))
    if golden_path:
        pairs.extend(_pairs_from_golden(Path(golden_path)))
    if signal_key_contains:
        needle = signal_key_contains.lower()
        pairs = [p for p in pairs if needle in str(p.get("signal_key") or "").lower()]
    return pairs


def _loss_for_params(
    pairs: Sequence[Dict[str, Any]],
    beta: float,
    gamma: float,
    steps: int = 10,
) -> Tuple[float, List[Dict[str, Any]]]:
    rows = []
    errs = []
    for p in pairs:
        sim = simulate_cultural_transmission(
            str(p.get("seed_term") or "signal"),
            beta=beta,
            gamma=gamma,
            steps=steps,
            virality_hybrid=float(p.get("virality_hybrid") or 0.5),
        )
        peak = float((sim.get("summary") or {}).get("peak_mean_adoption") or 0.0)
        target = float(p.get("outcome_value") or 0.0)
        err = abs(peak - target)
        errs.append(err)
        rows.append({
            "forecast_id": p.get("forecast_id"),
            "signal_key": p.get("signal_key"),
            "outcome_value": target,
            "peak_mean_adoption": round(peak, 4),
            "abs_error": round(err, 4),
        })
    mae = sum(errs) / len(errs) if errs else 1.0
    return mae, rows


def calibrate_transmission_params(
    *,
    golden_path: Optional[Path | str] = None,
    series: Optional[Dict[str, Any]] = None,
    signal_key_contains: Optional[str] = None,
    beta_grid: Optional[Sequence[float]] = None,
    gamma_grid: Optional[Sequence[float]] = None,
    steps: int = 10,
) -> Dict[str, Any]:
    """
    Grid-search advisory beta/gamma for cultural transmission.

    Returns best params + MAE. Label: SPECULATIVE. brier always null.
    """
    pairs = load_calibration_pairs(
        golden_path=golden_path,
        series=series,
        signal_key_contains=signal_key_contains,
    )
    if not pairs:
        return {
            "schema": "hyperlex.transmission_calibration.v1",
            "ok": False,
            "error": "no_settled_pairs",
            "brier": None,
            "provenance": "SPECULATIVE",
        }

    betas = list(beta_grid) if beta_grid is not None else [0.15, 0.25, 0.35, 0.45, 0.55, 0.65]
    gammas = list(gamma_grid) if gamma_grid is not None else [0.04, 0.08, 0.12, 0.18]
    best = None
    best_mae = 1e9
    best_rows: List[Dict[str, Any]] = []
    trials = []

    for b in betas:
        for g in gammas:
            mae, rows = _loss_for_params(pairs, float(b), float(g), steps=steps)
            trials.append({"beta": b, "gamma": g, "mae": round(mae, 5)})
            if mae < best_mae:
                best_mae = mae
                best = {"beta": float(b), "gamma": float(g)}
                best_rows = rows

    return {
        "schema": "hyperlex.transmission_calibration.v1",
        "ok": True,
        "n_pairs": len(pairs),
        "signal_key_filter": signal_key_contains,
        "best_params": best,
        "mae": round(best_mae, 5),
        "pair_diagnostics": best_rows,
        "grid_size": len(trials),
        "top_trials": sorted(trials, key=lambda t: t["mae"])[:5],
        "provenance": "SPECULATIVE",
        "brier": None,
        "note": (
            "Advisory params for future simulate_cultural_transmission calls. "
            "Does not invent Brier; does not rewrite settlements."
        ),
    }
