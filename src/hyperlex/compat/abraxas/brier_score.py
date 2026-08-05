"""BrierScorePacket.v1-compatible dicts (Abraxas core.brier.scores shape).

Implemented in Hyperlex. No Abraxas import. No pydantic required.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional


def compute_atomic_brier(expected_probability: float, observed_outcome: int | float) -> float:
    """Match Abraxas BrierScorePacket.compute_score (rounded to 6 dp)."""
    o = int(observed_outcome)
    return round((float(expected_probability) - o) ** 2, 6)


def compute_score_hash(
    forecast_hash: str,
    expected_probability: float,
    observed_outcome: int,
    brier_score: float,
) -> str:
    """Match Abraxas BrierScorePacket.compute_hash."""
    return hashlib.sha256(
        f"{forecast_hash}|{expected_probability:.6f}|{observed_outcome}|{brier_score:.6f}".encode()
    ).hexdigest()


def to_brier_score_packet(
    forecast: Dict[str, Any],
    score: Dict[str, Any],
    *,
    forecast_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build BrierScorePacket.v1-compatible dict from Hyperlex score_pair output.

    Fail-closed unless score status is SCORED.
    """
    if score.get("status") != "SCORED":
        raise ValueError(
            f"cannot build score packet when status={score.get('status')!r}; "
            "settlement required"
        )

    p = float(score["probability"])
    o = int(float(score["outcome_value"]))
    if o not in (0, 1):
        raise ValueError("observed_outcome must be 0 or 1")
    if not 0.0 <= p <= 1.0:
        raise ValueError("probability out of [0,1]")

    bs = compute_atomic_brier(p, o)
    # prefer provided atomic if present (should match)
    if "atomic_score" in score:
        # allow tiny float drift; packet uses rounded formula
        pass

    fh = forecast_hash or hashlib.sha256(
        f"{forecast.get('forecast_id')}|{p:.6f}".encode()
    ).hexdigest()
    det = compute_score_hash(fh, p, o, bs)
    score_id = hashlib.sha256(f"{fh}|{det}".encode()).hexdigest()[:24]

    return {
        "schema_version": "BrierScorePacket.v1",
        "score_id": score_id,
        "forecast_hash": fh,
        "expected_probability": p,
        "observed_outcome": o,
        "brier_score": bs,
        "deterministic_score_hash": det,
        "authority": {
            "kind": "operator",
            "source": "hyperlex",
            "locked": True,
        },
        "status": "ok",
        "hyperlex": {
            "forecast_id": forecast.get("forecast_id") or score.get("forecast_id"),
            "settlement_id": score.get("settlement_id"),
            "signal_key": forecast.get("signal_key") or score.get("signal_key"),
        },
    }
