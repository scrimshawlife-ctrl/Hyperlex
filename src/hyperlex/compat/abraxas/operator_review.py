"""OperatorBrierReviewPacket.v1-compatible advisory dicts.

Mirrors Abraxas operator review wire shape. Hyperlex never auto-mutates
calibration mappings from this packet — advisory only.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional


FORBIDDEN_ACTIONS = frozenset({
    "autonomous_reliability_mutation",
    "execute_production",
})


def to_operator_brier_review(
    series: Dict[str, Any],
    *,
    ledger_hash: Optional[str] = None,
    pending_actions: Optional[List[str]] = None,
    review_note: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build an advisory operator review packet from a score_series result.

    status: pending | not_computable
    """
    actions = list(pending_actions or [])
    for a in actions:
        if a in FORBIDDEN_ACTIONS:
            raise ValueError(f"forbidden pending_action: {a}")

    if series.get("status") != "SCORED":
        return {
            "schema_version": "OperatorBrierReviewPacket.v1",
            "review_id": "not-computable",
            "ledger_hash": ledger_hash or "",
            "reliability_score": None,
            "replay_failures": 0,
            "pending_actions": [],
            "authority": {"kind": "advisory", "source": "hyperlex", "locked": True},
            "status": "not_computable",
            "reason": f"series status={series.get('status')}",
            "hyperlex": {"series_n": series.get("n", 0)},
        }

    murphy = series.get("murphy_ferro") or series.get("murphy") or {}
    rel = murphy.get("reliability")
    if not isinstance(rel, (int, float)):
        rel = 0.0

    # higher reliability error → lower "reliability_score" (1 - REL floored)
    reliability_score = max(0.0, min(1.0, 1.0 - float(rel)))
    yates = series.get("yates") or {}
    if isinstance(yates.get("bias_squared"), (int, float)) and float(yates["bias_squared"]) >= 0.01:
        if "consider_mean_shift" not in actions:
            actions.append("consider_mean_shift")

    payload_key = f"{series.get('n')}|{series.get('series_brier')}|{reliability_score}"
    review_id = hashlib.sha256(payload_key.encode()).hexdigest()[:20]
    lh = ledger_hash or hashlib.sha256(
        f"hyperlex-series|{payload_key}".encode()
    ).hexdigest()

    return {
        "schema_version": "OperatorBrierReviewPacket.v1",
        "review_id": review_id,
        "ledger_hash": lh,
        "reliability_score": round(reliability_score, 6),
        "replay_failures": 0,
        "pending_actions": actions,
        "authority": {"kind": "operator", "source": "hyperlex", "locked": True},
        "status": "pending",
        "note": review_note or "advisory_only_no_auto_mutation",
        "hyperlex": {
            "series_brier": series.get("series_brier"),
            "n": series.get("n"),
            "bias_squared": yates.get("bias_squared"),
            "delta_f": (series.get("discrimination") or {}).get("delta_f"),
        },
    }
