"""Detector-side slang mutation grammar (spec 001 + 003).

Separate from ``hyperlex.analysis.mutation.predict_mutations``.
Never generates restricted wraps. Packets are never forecast-eligible.
"""
from .grammar import parse_mutation_trace
from .human import format_human_card
from .packet import MutationTracePacket, redact_packet, packet_id_for
from .watch import append_watch, read_watch_log, watch_score, watch_summary
from .operators import DETECTOR_OPS, LAYER_FOR_OP

__all__ = [
    "parse_mutation_trace",
    "format_human_card",
    "MutationTracePacket",
    "redact_packet",
    "packet_id_for",
    "watch_score",
    "append_watch",
    "read_watch_log",
    "watch_summary",
    "DETECTOR_OPS",
    "LAYER_FOR_OP",
]
