"""Legacy thin shim for backward compatibility.

All logic now lives in the symbolic dual-named structure:
intake / analysis / synthesis / receipt

See src/hyperlex/__init__.py and symbolic/ for the canonical architecture.
"""
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

# Re-export for old imports that did "from .engine import ..."
__all__ = [
    "ingest_signal",
    "detect_memetic_patterns",
    "mock_integrate_with_external_signal",
    "emit_receipt",
    "humanize_slang_output",
    "compute_virality_score",
    "simulate_hyperstition_loop",
]
