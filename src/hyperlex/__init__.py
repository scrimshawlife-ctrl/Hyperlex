"""Hyperlex — Memetic Emergence Engine.

Symbolic architecture (numogram + chaos-magic):
- intake (gate_of_intake) — expanded ingest
- analysis (zone_of_emergence)
- synthesis (current_of_transmission)
- receipt (archive_of_becoming)
- calibration (forecast → settlement → Brier)

Schemas available in .schemas
"""
from pathlib import Path


def _read_version() -> str:
    candidate = Path(__file__).resolve().parents[2] / "VERSION"
    if candidate.exists():
        return candidate.read_text(encoding="utf-8").strip() or "0.1.0"
    return "0.1.0"


PKG_VERSION = _read_version()

from .intake import ingest_signal, fetch_ingest
from .analysis import (
    humanize_slang_output,
    detect_neologisms,
    trace_semantic_variation,
    compute_virality_score,
    memetics_protocol_check,
    simulate_hyperstition_loop,
    detect_memetic_patterns,
    match_lineage,
    compute_lineage_confidence,
)
from .synthesis import mock_integrate_with_external_signal
from .receipt import emit_receipt
from . import schemas
from . import calibration
from .calibration import (
    extract_forecasts,
    settle,
    score_pair,
    score_series,
    NOT_COMPUTABLE,
)

__all__ = [
    "ingest_signal",
    "fetch_ingest",
    "detect_memetic_patterns",
    "match_lineage",
    "compute_lineage_confidence",
    "mock_integrate_with_external_signal",
    "emit_receipt",
    "humanize_slang_output",
    "compute_virality_score",
    "simulate_hyperstition_loop",
    "extract_forecasts",
    "settle",
    "score_pair",
    "score_series",
    "NOT_COMPUTABLE",
    "calibration",
    "schemas",
    "PKG_VERSION",
]

__version__ = PKG_VERSION
