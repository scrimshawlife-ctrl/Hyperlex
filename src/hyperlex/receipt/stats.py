"""Aggregate stats over the receipt ledger (operator view)."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

from .ledger import list_receipts, verify_ledger_chain, default_ledger_path


def ledger_stats(
    path: Optional[Path | str] = None,
    *,
    limit: int = 0,
) -> Dict[str, Any]:
    """
    Summarize receipt ledger index entries.

    limit=0 means all entries.
    """
    ledger = Path(path) if path else default_ledger_path()
    chain = verify_ledger_chain(ledger)
    rows = list_receipts(ledger, limit=limit if limit and limit > 0 else 10**9)

    families: Counter[str] = Counter()
    stages: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    with_lineage = 0
    confidences: List[float] = []

    for row in rows:
        fam = row.get("lineage_family")
        if fam:
            families[str(fam)] += 1
            with_lineage += 1
        else:
            families["unmatched"] += 1
        stage = row.get("hyperstition_risk")
        if stage:
            stages[str(stage)] += 1
        src = row.get("ingest_source")
        if src:
            sources[str(src)] += 1
        c = row.get("lineage_confidence")
        if isinstance(c, (int, float)):
            confidences.append(float(c))

    mean_conf = (sum(confidences) / len(confidences)) if confidences else None

    return {
        "schema": "hyperlex.ledger_stats.v1",
        "ledger_path": str(ledger),
        "chain_ok": bool(chain.get("ok")),
        "chain": chain,
        "n_entries": len(rows),
        "n_with_lineage": with_lineage,
        "n_unmatched": families.get("unmatched", 0),
        "families": dict(families.most_common()),
        "hyperstition_stages": dict(stages.most_common()),
        "ingest_sources": dict(sources.most_common()),
        "mean_lineage_confidence": round(mean_conf, 4) if mean_conf is not None else None,
        "tip_hash": chain.get("tip_hash"),
    }
