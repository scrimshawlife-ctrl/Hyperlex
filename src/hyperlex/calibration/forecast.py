"""Extract forecasts from Hyperlex analysis results."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

from .mapping import (
    MAPPING_VERSION,
    map_lineage_confidence,
    map_virality,
    map_hyperstition,
)


def _forecast_id(receipt_integrity: str, signal_key: str, probability: float) -> str:
    raw = f"{receipt_integrity}|{signal_key}|{probability:.6f}|{MAPPING_VERSION}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def extract_forecasts(
    result: Dict[str, Any],
    *,
    receipt_ref: Optional[Dict[str, str]] = None,
    mapping_version: str = MAPPING_VERSION,
    hyperstition_stage_map: Optional[Mapping[str, float]] = None,
) -> List[Dict[str, Any]]:
    """
    Pure extraction of forecast objects from an analysis result.

    Does not write files. Does not compute Brier scores.

    hyperstition_stage_map: optional override for EMERGENT/ACTUALIZING → f
    (from connectors.hyperstition_feedback; future forecasts only).
    """
    # Allow v1 and explicit feedback-suffixed versions that still use v1 maps
    if mapping_version != MAPPING_VERSION and not str(mapping_version).startswith(MAPPING_VERSION):
        return []

    analysis = result.get("analysis") or {}
    prov = result.get("provenance") or {}
    integrity = (receipt_ref or {}).get("integrity") or prov.get("canonical_hash") or "unknown"
    created = prov.get("timestamp") or datetime.now(timezone.utc).isoformat()

    forecasts: List[Dict[str, Any]] = []

    # lineage.confidence
    mapped = map_lineage_confidence(analysis.get("lineage"))
    if mapped:
        prob, ctx = mapped
        family = ctx.get("family_id") or "unknown"
        forecasts.append({
            "forecast_id": _forecast_id(integrity, "lineage.confidence", prob),
            "receipt_ref": {
                "path": (receipt_ref or {}).get("path"),
                "integrity": integrity,
                "canonical_hash": prov.get("canonical_hash"),
            },
            "signal_key": "lineage.confidence",
            "probability": round(prob, 6),
            "target_event": f"Lineage family '{family}' membership confirmed on review",
            "target_schema": "lineage.family_confirmed",
            "created_at": created,
            "mapping_version": mapping_version,
            "provenance": "INFERRED",
            "context": ctx,
        })

    # virality.hybrid_score
    mapped = map_virality(analysis.get("virality"))
    if mapped:
        prob, ctx = mapped
        forecasts.append({
            "forecast_id": _forecast_id(integrity, "virality.hybrid_score", prob),
            "receipt_ref": {
                "path": (receipt_ref or {}).get("path"),
                "integrity": integrity,
                "canonical_hash": prov.get("canonical_hash"),
            },
            "signal_key": "virality.hybrid_score",
            "probability": round(prob, 6),
            "target_event": "Observed uptake / engagement above threshold in evaluation window",
            "target_schema": "uptake.observed",
            "created_at": created,
            "mapping_version": mapping_version,
            "provenance": "INFERRED",
            "context": ctx,
        })

    # hyperstition.stage (optional feedback override map)
    if hyperstition_stage_map is not None:
        from ..connectors.hyperstition_feedback import map_hyperstition_with_override

        mapped = map_hyperstition_with_override(
            analysis.get("hyperstition"),
            stage_map=hyperstition_stage_map,
        )
    else:
        mapped = map_hyperstition(analysis.get("hyperstition"))
    if mapped:
        prob, ctx = mapped
        forecasts.append({
            "forecast_id": _forecast_id(integrity, "hyperstition.stage", prob),
            "receipt_ref": {
                "path": (receipt_ref or {}).get("path"),
                "integrity": integrity,
                "canonical_hash": prov.get("canonical_hash"),
            },
            "signal_key": "hyperstition.stage",
            "probability": round(prob, 6),
            "target_event": "Hyperstition loop later confirmed by cultural or market evidence",
            "target_schema": "hyperstition.loop_confirmed",
            "created_at": created,
            "mapping_version": mapping_version,
            "provenance": "SPECULATIVE",
            "context": ctx,
        })

    return forecasts
