"""Optional export shapes compatible with Abraxas BrierLedgerEntry.

No Abraxas import. Field names and hash formula mirror
Abraxas-v2.0 `core/brier/ledger.py` so operators can hand-off entries.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_ledger_hash(
    forecast_hash: str,
    score_hash: str,
    calibration_hash: str,
    ledger_generation: int,
) -> str:
    """Match Abraxas BrierLedgerEntry.compute_hash."""
    return _sha256(f"{forecast_hash}|{score_hash}|{calibration_hash}|{ledger_generation}")


def to_brier_ledger_entry(
    forecast: Dict[str, Any],
    score: Dict[str, Any],
    *,
    settlement: Optional[Dict[str, Any]] = None,
    ledger_generation: int = 1,
    calibration_note: str = "hyperlex.calibration.v1",
) -> Dict[str, Any]:
    """
    Build a BrierLedgerEntry.v1-compatible dict from a Hyperlex scored pair.

    Only valid when score["status"] == "SCORED". Otherwise raises ValueError
    (fail-closed — never export a fabricated score).
    """
    if score.get("status") != "SCORED":
        raise ValueError(
            f"cannot export ledger entry when score status={score.get('status')!r}; "
            "settlement required"
        )

    forecast_id = str(forecast.get("forecast_id") or score.get("forecast_id") or "")
    settlement_id = str(
        (settlement or {}).get("settlement_id") or score.get("settlement_id") or ""
    )

    forecast_hash = _sha256(
        _canonical({
            "forecast_id": forecast_id,
            "probability": forecast.get("probability", score.get("probability")),
            "signal_key": forecast.get("signal_key", score.get("signal_key")),
            "mapping_version": forecast.get("mapping_version"),
            "receipt_integrity": (forecast.get("receipt_ref") or {}).get("integrity"),
        })
    )
    score_hash = _sha256(
        _canonical({
            "forecast_id": forecast_id,
            "settlement_id": settlement_id,
            "atomic_score": score.get("atomic_score"),
            "probability": score.get("probability"),
            "outcome_value": score.get("outcome_value"),
        })
    )
    calibration_hash = _sha256(
        _canonical({
            "note": calibration_note,
            "signal_key": forecast.get("signal_key", score.get("signal_key")),
            "mapping_version": forecast.get("mapping_version"),
        })
    )
    det = compute_ledger_hash(forecast_hash, score_hash, calibration_hash, ledger_generation)
    ledger_entry_id = _sha256(f"{forecast_id}|{settlement_id}|{ledger_generation}")[:32]

    return {
        "schema_version": "BrierLedgerEntry.v1",
        "ledger_entry_id": ledger_entry_id,
        "forecast_hash": forecast_hash,
        "score_hash": score_hash,
        "calibration_hash": calibration_hash,
        "replay_hash": None,
        "ledger_generation": ledger_generation,
        "deterministic_ledger_hash": det,
        "authority": {
            "kind": ((settlement or {}).get("authority") or {}).get("kind", "operator"),
            "source": "hyperlex",
        },
        "status": "recorded",
        # Hyperlex provenance (extra; Abraxas ignores unknown if strict — keep under hyperlex)
        "hyperlex": {
            "forecast_id": forecast_id,
            "settlement_id": settlement_id,
            "atomic_score": score.get("atomic_score"),
            "signal_key": forecast.get("signal_key", score.get("signal_key")),
        },
    }
