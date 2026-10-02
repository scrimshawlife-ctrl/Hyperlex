"""HYPERLEX_INSTRUMENT_V1 — representation and measurement layer.

Primary operation: ``observe(text) -> HyperlexObservation``.
Not a classifier. Advisory evidence only.
"""

from .capabilities import capabilities
from .constants import (
    CLASSIFIER_RELEASE,
    CONTRACT_VERSION,
    INSTRUMENT_READINESS,
    INSTRUMENT_VERSION,
    OPERATION_MODE,
    PRODUCT_ROLE,
)
from .manifest import cold_load_manifest
from .runtime import get_capabilities, get_manifest, health, observe
from .sdk import InstrumentClient, InstrumentHttpClient
from .validate import validate_observation

__all__ = [
    "INSTRUMENT_VERSION",
    "CONTRACT_VERSION",
    "PRODUCT_ROLE",
    "OPERATION_MODE",
    "CLASSIFIER_RELEASE",
    "INSTRUMENT_READINESS",
    "observe",
    "health",
    "get_manifest",
    "get_capabilities",
    "capabilities",
    "cold_load_manifest",
    "validate_observation",
    "InstrumentClient",
    "InstrumentHttpClient",
]
