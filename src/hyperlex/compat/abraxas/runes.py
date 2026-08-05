"""Hyperlex rune catalog + envelope builders (Abraxas-bindable wire shapes).

Host systems bind by rune_id. No Abraxas import.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...relay import (
    list_runes,
    relay_from_result,
    relay_forecasts,
    relay_series,
    RUNE_LIVE_EMERGENCE,
    RUNE_COMMUNICATION_RELAY,
    RUNE_CALIBRATION_FORECAST,
    RUNE_CALIBRATION_SERIES,
)


def list_hlx_runes() -> List[Dict[str, str]]:
    """Alias of hyperlex.relay.list_runes for Abraxas-facing imports."""
    return list_runes()


def envelopes_from_result(
    result: Dict[str, Any],
    *,
    include_signal: bool = True,
    include_scan: bool = True,
    include_forecasts: bool = False,
    forecasts: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Emit bindable rune envelopes from an analysis result."""
    envs = relay_from_result(
        result,
        include_signal=include_signal,
        include_scan=include_scan,
    )
    if include_forecasts:
        fcs = forecasts if forecasts is not None else []
        envs.append(relay_forecasts(fcs))
    return envs


def envelope_from_series(series: Dict[str, Any]) -> Dict[str, Any]:
    return relay_series(series)


__all__ = [
    "list_hlx_runes",
    "envelopes_from_result",
    "envelope_from_series",
    "RUNE_LIVE_EMERGENCE",
    "RUNE_COMMUNICATION_RELAY",
    "RUNE_CALIBRATION_FORECAST",
    "RUNE_CALIBRATION_SERIES",
]
