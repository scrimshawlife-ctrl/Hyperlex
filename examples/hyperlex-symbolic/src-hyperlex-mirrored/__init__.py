"""Hyperlex — Memetic Emergence Engine

Symbolic architecture (numogram + chaos-magic):
- intake: gate_of_intake
- analysis: zone_of_emergence  
- synthesis: current_of_transmission
- receipt: archive_of_becoming

See symbolic/ for full curated correspondence and diagrams.
"""
from importlib.metadata import version as _pkg_version
try:
    PKG_VERSION = _pkg_version("hyperlex")
except Exception:
    PKG_VERSION = "1.5.0"

# Re-export public API from symbolic modules
from .intake import ingest_signal
from .analysis import (
    humanize_slang_output,
    detect_neologisms,
    trace_semantic_variation,
    compute_virality_score,
    memetics_protocol_check,
    simulate_hyperstition_loop,
    detect_memetic_patterns,
)
from .synthesis import mock_integrate_with_external_signal
from .receipt import emit_receipt

__all__ = [
    "ingest_signal",
    "detect_memetic_patterns",
    "mock_integrate_with_external_signal",
    "emit_receipt",
    "humanize_slang_output",
    "compute_virality_score",
    "simulate_hyperstition_loop",
    "PKG_VERSION",
]

__version__ = PKG_VERSION
