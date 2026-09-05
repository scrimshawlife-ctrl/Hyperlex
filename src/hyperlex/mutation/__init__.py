"""Detector-side slang mutation grammar (spec 001).

Separate from ``hyperlex.analysis.mutation.predict_mutations``.
Never generates restricted wraps. Packets are never forecast-eligible.
"""
from .grammar import parse_mutation_trace
from .packet import MutationTracePacket, redact_packet, packet_id_for
from .watch import watch_score
from .operators import DETECTOR_OPS, LAYER_FOR_OP

__all__ = [
    "parse_mutation_trace",
    "MutationTracePacket",
    "redact_packet",
    "packet_id_for",
    "watch_score",
    "DETECTOR_OPS",
    "LAYER_FOR_OP",
]
