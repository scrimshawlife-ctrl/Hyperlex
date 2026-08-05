"""Generic outbound connectors (no host hard-deps).

Market-signal and forecast-pipeline packets for external systems.
Hyperstition feedback advises future forecast mappings only.
"""

from .market_signal import build_market_signal, build_forecast_pipeline
from .hyperstition_feedback import (
    hyperstition_feedback_from_series,
    apply_stage_map_override,
)

__all__ = [
    "build_market_signal",
    "build_forecast_pipeline",
    "hyperstition_feedback_from_series",
    "apply_stage_map_override",
]
