"""Compatibility adapters for external systems.

Hyperlex is a **standalone app**. It does not import Abraxas, Hollersports,
or Orchestra. Relevant Abraxas *shapes* (Brier ledger, score packets, claim
labels, operator review, rune envelopes) are implemented here as pure Hyperlex
modules so Abraxas (or any host) can import *from hyperlex* if desired.

Usage:
    from hyperlex.compat.abraxas import (
        to_brier_ledger_entry,
        to_brier_score_packet,
        CLAIM_LABELS,
        list_hlx_runes,
    )
"""

from . import abraxas

__all__ = ["abraxas"]
