"""Mermaid diagram generation from receipts and ledgers.

Pure string builders — no network, no Abraxas. Diagrams are OBSERVED
structure when built from real receipt indexes; family labels from lineage
matcher remain INFERRED.
"""

from __future__ import annotations

from .from_receipts import (
    diagram_lineage_distribution,
    diagram_receipt_timeline,
    diagram_receipt_flow,
    diagram_from_ledger,
    diagram_from_receipt_files,
    write_diagram_bundle,
)

__all__ = [
    "diagram_lineage_distribution",
    "diagram_receipt_timeline",
    "diagram_receipt_flow",
    "diagram_from_ledger",
    "diagram_from_receipt_files",
    "write_diagram_bundle",
]
