"""Relevant Abraxas-compatible capabilities as Hyperlex modules.

No `import abraxas` / `import core.*`. Dict schemas mirror Abraxas v2 wire
shapes so packets can cross the boundary without shared runtime.

Modules
-------
claims            OBSERVED | INFERRED | SPECULATIVE | NOT_COMPUTABLE
brier_ledger      BrierLedgerEntry.v1
brier_score       BrierScorePacket.v1
operator_review   OperatorBrierReviewPacket.v1 (advisory only)
runes             RUNE.HLX.* catalog + envelope builders
"""

from .claims import CLAIM_LABELS, label_claim, NOT_COMPUTABLE
from .brier_ledger import to_brier_ledger_entry, compute_ledger_hash
from .brier_score import to_brier_score_packet, compute_atomic_brier
from .operator_review import to_operator_brier_review
from .runes import list_hlx_runes, envelopes_from_result, envelope_from_series

__all__ = [
    "CLAIM_LABELS",
    "label_claim",
    "NOT_COMPUTABLE",
    "to_brier_ledger_entry",
    "compute_ledger_hash",
    "to_brier_score_packet",
    "compute_atomic_brier",
    "to_operator_brier_review",
    "list_hlx_runes",
    "envelopes_from_result",
    "envelope_from_series",
]
