"""Generic market / narrative signal + forecast pipeline packets.

Host-agnostic JSON. No Abraxas/Hollersports import.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..synthesis import mock_integrate_with_external_signal
from ..calibration.forecast import extract_forecasts


def _sha(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_market_signal(
    result: Dict[str, Any],
    *,
    domain: str = "narrative",
) -> Dict[str, Any]:
    """
    Compress analysis into a generic market/narrative signal packet.

    actionable: MONITOR | IGNORE | ESCALATE (advisory only — not execution authority)
    """
    base = mock_integrate_with_external_signal(result)
    analysis = result.get("analysis") or {}
    lineage = analysis.get("lineage") or {}
    prov = result.get("provenance") or {}
    hyper = analysis.get("hyperstition") or {}

    hybrid = float(base.get("virality_boost") or 0.0)
    stage = str(hyper.get("loop_stage") or base.get("hyperstition_risk") or "EMERGENT").upper()
    conf = float(base.get("confidence") or 0.0)

    if stage == "ACTUALIZING" and hybrid >= 0.6:
        actionable = "ESCALATE"
    elif base.get("actionable") == "MONITOR" or hybrid >= 0.55:
        actionable = "MONITOR"
    else:
        actionable = "IGNORE"

    packet = {
        "schema": "hyperlex.market_signal.v1",
        "signal_id": base.get("signal_id") or f"hlx_{prov.get('canonical_hash', 'unk')}",
        "created_at": prov.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        "domain": domain,
        "actionable": actionable,
        "confidence": conf,
        "virality_boost": hybrid,
        "hyperstition_stage": stage,
        "hyperstition_mechanism": hyper.get("mechanism") or base.get("hyperstition_mechanism"),
        "lineage_family": lineage.get("family_id"),
        "lineage_confidence": lineage.get("confidence"),
        "source_fingerprint": (prov.get("source_fingerprint") or {}).get("fingerprint_id"),
        "canonical_hash": prov.get("canonical_hash"),
        "brier": None,  # never invent
        "brier_note": "brier_requires_settlement",
        "authority": "advisory",
        "observed_preview": (result.get("observed") or "")[:200],
        "claims": [
            {"statement": "virality_boost", "label": "INFERRED"},
            {"statement": "hyperstition_stage", "label": "SPECULATIVE"},
            {"statement": "actionable", "label": "INFERRED"},
            {"statement": "brier", "label": "NOT_COMPUTABLE"},
        ],
    }
    packet["packet_hash"] = _sha({k: v for k, v in packet.items() if k != "packet_hash"})[:24]
    return packet


def build_forecast_pipeline(
    result: Dict[str, Any],
    *,
    forecasts: Optional[List[Dict[str, Any]]] = None,
    market_signal: Optional[Dict[str, Any]] = None,
    series: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Handoff packet for external forecast / market systems.

    Includes forecasts (no scores) + optional market signal + optional settled series.
    """
    fcs = forecasts if forecasts is not None else extract_forecasts(result)
    sig = market_signal if market_signal is not None else build_market_signal(result)
    prov = result.get("provenance") or {}

    series_status = (series or {}).get("status", "NOT_COMPUTABLE")
    packet = {
        "schema": "hyperlex.forecast_pipeline.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "canonical_hash": prov.get("canonical_hash"),
        "source_fingerprint": (prov.get("source_fingerprint") or {}).get("fingerprint_id"),
        "n_forecasts": len(fcs),
        "forecasts": fcs,
        "market_signal": sig,
        "series": series if series else {"status": "NOT_COMPUTABLE", "n": 0, "note": "no_settled_series_attached"},
        "series_status": series_status,
        "authority": "advisory",
        "notes": [
            "Forecasts are probabilities only until operator settlement.",
            "Do not treat actionable=ESCALATE as execution authority.",
        ],
    }
    packet["packet_hash"] = _sha({k: v for k, v in packet.items() if k != "packet_hash"})[:24]
    return packet
