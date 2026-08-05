"""Hyperstition loop feedback into future forecast mappings.

Uses settled score_series for signal_key=hyperstition.stage (or any series
whose cohort carries that key) to advise an updated discrete stage→f map.

Never rewrites historical forecasts. Advisory only until an operator bumps
mapping_version / adopts the override for new extractions.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, MutableMapping, Optional

from ..calibration.mapping import HYPERSTITION_STAGE_PROB, MAPPING_VERSION
from ..calibration.recalibrate import mean_shift_from_series

# Stages eligible for feedback
STAGES = ("EMERGENT", "ACTUALIZING")


def hyperstition_feedback_from_series(
    series: Dict[str, Any],
    *,
    base_map: Optional[Mapping[str, float]] = None,
    max_step: float = 0.08,
) -> Dict[str, Any]:
    """
    Derive advisory stage-probability map from a settled series.

    Uses Yates mean bias (mean_f − mean_o) as a global shift applied to each
    stage probability, clamped to [0.05, 0.95], with max per-stage step.

    Returns status ADVISORY | NOT_COMPUTABLE.
    """
    base = dict(base_map or HYPERSTITION_STAGE_PROB)
    if series.get("status") != "SCORED" or int(series.get("n") or 0) < 1:
        return {
            "status": "NOT_COMPUTABLE",
            "reason": f"series status={series.get('status')} n={series.get('n')}",
            "mapping_version_current": MAPPING_VERSION,
            "base_map": base,
            "advised_map": None,
            "apply": "none",
        }

    shift_info = mean_shift_from_series(series)
    # mean_shift = mean_o - mean_f  (add to future f)
    shift = shift_info.get("shift")
    if not isinstance(shift, (int, float)):
        return {
            "status": "NOT_COMPUTABLE",
            "reason": "shift_not_computable",
            "mapping_version_current": MAPPING_VERSION,
            "base_map": base,
            "advised_map": None,
            "apply": "none",
            "mean_shift": shift_info,
        }

    # Cap step to avoid violent map jumps from small n
    step = max(-max_step, min(max_step, float(shift)))
    advised: Dict[str, float] = {}
    for stage, p in base.items():
        np = max(0.05, min(0.95, float(p) + step))
        advised[stage] = round(np, 4)

    yates = series.get("yates") or {}
    return {
        "status": "ADVISORY",
        "mapping_version_current": MAPPING_VERSION,
        "mapping_version_next_hint": f"{MAPPING_VERSION}+hyperstition_feedback",
        "base_map": base,
        "advised_map": advised,
        "shift_applied": step,
        "mean_shift": shift_info,
        "series_n": series.get("n"),
        "series_brier": series.get("series_brier"),
        "bias_squared": yates.get("bias_squared"),
        "apply": "future_forecasts_only",
        "note": (
            "Do not rewrite historical forecasts. Adopt advised_map only for new "
            "extract_forecasts calls (pass stage_map_override) and consider bumping "
            "mapping_version."
        ),
    }


def apply_stage_map_override(
    stage: str,
    *,
    stage_map: Optional[Mapping[str, float]] = None,
) -> Optional[float]:
    """Look up f for a hyperstition stage under an override map."""
    m = stage_map or HYPERSTITION_STAGE_PROB
    key = str(stage or "").upper()
    if key not in m:
        return None
    p = float(m[key])
    if not 0.0 <= p <= 1.0:
        return None
    return p


def map_hyperstition_with_override(
    hyper: Optional[Dict[str, Any]],
    *,
    stage_map: Optional[Mapping[str, float]] = None,
) -> Optional[tuple]:
    """Like mapping.map_hyperstition but with optional override map."""
    if not hyper:
        return None
    stage = str(hyper.get("loop_stage", "")).upper()
    p = apply_stage_map_override(stage, stage_map=stage_map)
    if p is None:
        return None
    return p, {"loop_stage": stage, "mechanism": hyper.get("mechanism"), "map_override": stage_map is not None}
