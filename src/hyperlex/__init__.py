"""Hyperlex — Memetic Emergence Engine (v1.6)

Symbolic architecture (numogram + chaos-magic):
- intake (gate_of_intake) — expanded ingest
- analysis (zone_of_emergence)
- synthesis (current_of_transmission)
- receipt (archive_of_becoming)

Schemas available in .schemas
"""
from importlib.metadata import version as _pkg_version
try:
    PKG_VERSION = _pkg_version("hyperlex")
except Exception:
    PKG_VERSION = "1.6.0"

# Re-exports
from .intake import ingest_signal, fetch_ingest
from .analysis import (
    compute_memetic_efficiency_score,
    humanize_slang_output,
    detect_neologisms,
    trace_semantic_variation,
    compute_virality_score,
    memetics_protocol_check,
    simulate_hyperstition_loop,
    detect_memetic_patterns,
    classify_compression_type,
    compute_context_friction,
    detect_memetic_memory_patterns,
)
from .synthesis import mock_integrate_with_external_signal
from .receipt import emit_receipt

# Schema access
from . import schemas

__all__ = [
    "ingest_signal",
    "fetch_ingest",
    "detect_memetic_patterns",
    "mock_integrate_with_external_signal",
    "emit_receipt",
    "humanize_slang_output",
    "compute_virality_score",
    "simulate_hyperstition_loop",
    "classify_compression_type",
    "compute_context_friction",
    "detect_memetic_memory_patterns",
    "compute_memetic_efficiency_score",
    "schemas",
    "PKG_VERSION",
]

__version__ = PKG_VERSION
