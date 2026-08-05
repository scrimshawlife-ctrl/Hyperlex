"""Settlement records for Hyperlex forecasts."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def is_scorable(settlement: Dict[str, Any]) -> bool:
    decision = str(settlement.get("settlement_decision", "")).upper()
    return decision in ("TRUE", "FALSE")


def settle(
    forecast: Dict[str, Any],
    *,
    outcome_value: float,
    settlement_decision: str,
    authority_kind: str = "operator",
    authority_ref: Optional[str] = None,
    authority_note: Optional[str] = None,
    evidence_ref: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a settlement object for a forecast.

    outcome_value must be 0.0 or 1.0.
    settlement_decision: TRUE | FALSE | VOID | CONFLICT
    Only TRUE/FALSE are later scored.
    """
    if outcome_value not in (0.0, 1.0):
        raise ValueError("outcome_value must be 0.0 or 1.0")
    decision = settlement_decision.upper()
    if decision not in ("TRUE", "FALSE", "VOID", "CONFLICT"):
        raise ValueError("settlement_decision must be TRUE|FALSE|VOID|CONFLICT")

    forecast_id = forecast["forecast_id"]
    settled_at = datetime.now(timezone.utc).isoformat()
    raw = f"{forecast_id}|{outcome_value}|{decision}|{settled_at}"
    settlement_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    return {
        "settlement_id": settlement_id,
        "forecast_id": forecast_id,
        "outcome_value": float(outcome_value),
        "settlement_decision": decision,
        "settled_at": settled_at,
        "authority": {
            "kind": authority_kind,
            "ref": authority_ref,
            "note": authority_note,
        },
        "evidence_ref": evidence_ref,
    }
