"""Rune / signal-relay wiring for Hyperlex.

Maps analysis results to Hermetic/Abraxas-compatible **rune envelopes** without
importing Abraxas. Downstream systems bind envelopes by `rune_id` + schema.

Primary runes:
  RUNE.HLX.LIVE_EMERGENCE_SCAN   — scan / analyze output
  RUNE.HLX.COMMUNICATION_RELAY  — virality + hyperstition → external signal
  RUNE.HLX.CALIBRATION_FORECAST — forecast extraction handoff
  RUNE.HLX.CALIBRATION_SERIES   — settled Brier series handoff
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..synthesis import mock_integrate_with_external_signal

RELAY_SCHEMA = "hyperlex.rune_envelope.v1"
RELAY_VERSION = "v1"

RUNE_LIVE_EMERGENCE = "RUNE.HLX.LIVE_EMERGENCE_SCAN"
RUNE_COMMUNICATION_RELAY = "RUNE.HLX.COMMUNICATION_RELAY"
RUNE_CALIBRATION_FORECAST = "RUNE.HLX.CALIBRATION_FORECAST"
RUNE_CALIBRATION_SERIES = "RUNE.HLX.CALIBRATION_SERIES"

CATALOG: Dict[str, Dict[str, str]] = {
    RUNE_LIVE_EMERGENCE: {
        "role": "scan",
        "description": "Memetic emergence scan result ready for archive/relay",
    },
    RUNE_COMMUNICATION_RELAY: {
        "role": "signal",
        "description": "Virality + hyperstition compressed into actionable signal",
    },
    RUNE_CALIBRATION_FORECAST: {
        "role": "forecast",
        "description": "Forecasts extracted from analysis (no Brier yet)",
    },
    RUNE_CALIBRATION_SERIES: {
        "role": "calibration",
        "description": "Settled Brier series (SCORED or NOT_COMPUTABLE)",
    },
}


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _envelope_id(rune_id: str, payload: Dict[str, Any]) -> str:
    raw = f"{rune_id}|{_canonical(payload)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def build_envelope(
    rune_id: str,
    payload: Dict[str, Any],
    *,
    authority: str = "advisory",
    provenance: Optional[Dict[str, Any]] = None,
    claims: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Pure envelope builder. Never invents Brier scores."""
    if rune_id not in CATALOG:
        raise ValueError(f"unknown rune_id: {rune_id}")
    meta = CATALOG[rune_id]
    created = datetime.now(timezone.utc).isoformat()
    body = {
        "schema": RELAY_SCHEMA,
        "relay_version": RELAY_VERSION,
        "rune_id": rune_id,
        "role": meta["role"],
        "description": meta["description"],
        "created_at": created,
        "authority": authority,  # advisory | operator | automated
        "payload": payload,
        "provenance": provenance or {},
        "claims": claims or [],
    }
    body["envelope_id"] = _envelope_id(rune_id, body)
    return body


def relay_from_result(
    result: Dict[str, Any],
    *,
    include_signal: bool = True,
    include_scan: bool = True,
) -> List[Dict[str, Any]]:
    """Emit rune envelopes from an analysis result."""
    envelopes: List[Dict[str, Any]] = []
    prov = result.get("provenance") or {}
    analysis = result.get("analysis") or {}
    lineage = analysis.get("lineage") or {}

    base_prov = {
        "canonical_hash": prov.get("canonical_hash"),
        "source_fingerprint": prov.get("source_fingerprint"),
        "ingest_source": prov.get("ingest_source"),
        "version": prov.get("version"),
        "brier": prov.get("brier"),  # null on open analysis
        "receipt_integrity": (result.get("receipt") or {}).get("integrity"),
    }

    if include_scan:
        scan_payload = {
            "observed_preview": (result.get("observed") or "")[:200],
            "lineage_family": lineage.get("family_id"),
            "lineage_confidence": lineage.get("confidence"),
            "virality": analysis.get("virality"),
            "memetics": analysis.get("memetics"),
            "hyperstition": analysis.get("hyperstition"),
            "neologism_count": len(analysis.get("neologisms") or []),
        }
        envelopes.append(
            build_envelope(
                RUNE_LIVE_EMERGENCE,
                scan_payload,
                provenance=base_prov,
                claims=[
                    {"statement": "scan_completed", "label": "OBSERVED"},
                    {
                        "statement": "lineage_match",
                        "label": "INFERRED" if lineage else "NOT_COMPUTABLE",
                    },
                    {"statement": "brier", "label": "NOT_COMPUTABLE"},
                ],
            )
        )

    if include_signal:
        signal = mock_integrate_with_external_signal(result)
        signal["relay_compatible"] = True
        signal["rune_bind"] = RUNE_COMMUNICATION_RELAY
        envelopes.append(
            build_envelope(
                RUNE_COMMUNICATION_RELAY,
                signal,
                provenance=base_prov,
                claims=[
                    {"statement": "virality_boost", "label": "INFERRED"},
                    {"statement": "hyperstition_risk", "label": "SPECULATIVE"},
                    {
                        "statement": "actionable",
                        "label": "INFERRED",
                    },
                ],
            )
        )

    return envelopes


def relay_forecasts(
    forecasts: List[Dict[str, Any]],
    *,
    receipt_ref: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Envelope for extracted forecasts (still unsettled)."""
    return build_envelope(
        RUNE_CALIBRATION_FORECAST,
        {
            "n_forecasts": len(forecasts),
            "forecasts": forecasts,
            "receipt_ref": receipt_ref,
            "brier": None,
            "note": "brier_requires_settlement",
        },
        claims=[
            {"statement": "forecasts_extracted", "label": "INFERRED"},
            {"statement": "brier", "label": "NOT_COMPUTABLE"},
        ],
    )


def relay_series(series: Dict[str, Any]) -> Dict[str, Any]:
    """Envelope for score_series / recompute_series output."""
    status = series.get("status", "NOT_COMPUTABLE")
    label = "OBSERVED" if status == "SCORED" else "NOT_COMPUTABLE"
    return build_envelope(
        RUNE_CALIBRATION_SERIES,
        series,
        authority="operator" if status == "SCORED" else "advisory",
        claims=[
            {"statement": "series_brier", "label": label},
            {"statement": "n", "label": "OBSERVED" if series.get("n") else "NOT_COMPUTABLE"},
        ],
    )


def list_runes() -> List[Dict[str, str]]:
    return [{"rune_id": k, **v} for k, v in CATALOG.items()]


__all__ = [
    "RELAY_SCHEMA",
    "RELAY_VERSION",
    "RUNE_LIVE_EMERGENCE",
    "RUNE_COMMUNICATION_RELAY",
    "RUNE_CALIBRATION_FORECAST",
    "RUNE_CALIBRATION_SERIES",
    "CATALOG",
    "build_envelope",
    "relay_from_result",
    "relay_forecasts",
    "relay_series",
    "list_runes",
]
