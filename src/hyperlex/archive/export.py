"""Export sanitized long-term analysis archive from receipts + ledger."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..receipt.ledger import default_ledger_path, list_receipts, verify_ledger_chain
from ..receipt.stats import ledger_stats


def sanitize_receipt_summary(
    receipt: Dict[str, Any],
    *,
    max_observed: int = 240,
) -> Dict[str, Any]:
    """
    Reduce a full receipt to a publish-safe summary for long-term analysis.

    Drops bulk raw_signal / full observed text beyond preview.
    Keeps hashes, lineage, typology, virality metrics, hyperstition stage.
    """
    prov = receipt.get("provenance") or {}
    analysis = receipt.get("analysis") or {}
    lineage = analysis.get("lineage") or {}
    mem = analysis.get("memetics") or {}
    vir = analysis.get("virality") or {}
    hyper = analysis.get("hyperstition") or {}
    rec = receipt.get("receipt") or {}
    ingest = receipt.get("ingest") or {}
    observed = str(receipt.get("observed") or "")

    return {
        "integrity": rec.get("integrity"),
        "canonical_hash": prov.get("canonical_hash"),
        "timestamp": prov.get("timestamp"),
        "version": prov.get("version"),
        "ingest_source": prov.get("ingest_source") or ingest.get("source"),
        "query": ingest.get("query"),
        "source_fingerprint_id": (prov.get("source_fingerprint") or {}).get("fingerprint_id"),
        "brier": prov.get("brier"),  # should be null on open receipts
        "lineage_family": lineage.get("family_id"),
        "lineage_confidence": lineage.get("confidence"),
        "matched_terms": (lineage.get("matched_terms") or [])[:12],
        "typology": mem.get("typology_primary") or mem.get("typology"),
        "is_memetic": mem.get("is_memetic"),
        "virality_hybrid": vir.get("hybrid_score"),
        "virality_predicted": (vir.get("prediction") or {}).get("predicted_hybrid"),
        "hyperstition_stage": hyper.get("loop_stage") or prov.get("hyperstition_risk"),
        "n_neologisms": len(analysis.get("neologisms") or []),
        "observed_preview": observed[:max_observed],
        "epistemic": {
            "lineage": "INFERRED" if lineage else "NOT_COMPUTABLE",
            "virality_prediction": "SPECULATIVE",
            "brier": "NOT_COMPUTABLE" if prov.get("brier") is None else "REQUIRES_SERIES",
        },
    }


def _load_receipt_files(paths: Sequence[Path]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in paths:
        if not p.exists() or p.suffix != ".json" or p.name == "MANIFEST.json":
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and ("analysis" in data or "provenance" in data):
            out.append(data)
    return out


def export_analysis_archive(
    *,
    out_dir: Path | str,
    ledger_path: Optional[Path | str] = None,
    receipt_dirs: Optional[Sequence[Path | str]] = None,
    receipt_files: Optional[Sequence[Path | str]] = None,
    include_ledger_index: bool = True,
    snapshot_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Write a long-term analysis archive bundle.

    Structure:
      out_dir/
        index.json          — snapshot metadata + stats
        ledger_index.jsonl  — sanitized ledger rows (optional)
        receipts/*.json     — per-receipt sanitized summaries
        README.md           — human index for MkDocs / browsing
    """
    out = Path(out_dir)
    receipts_out = out / "receipts"
    receipts_out.mkdir(parents=True, exist_ok=True)

    snap = snapshot_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ledger = Path(ledger_path) if ledger_path else default_ledger_path()

    # Collect full receipts from dirs/files
    files: List[Path] = []
    for d in receipt_dirs or []:
        dp = Path(d)
        if dp.is_dir():
            files.extend(sorted(dp.glob("*.json")))
    for f in receipt_files or []:
        files.append(Path(f))

    full_receipts = _load_receipt_files(files)
    summaries = [sanitize_receipt_summary(r) for r in full_receipts]

    # Also pull ledger index (may cover more than on-disk files in out_dir)
    ledger_rows = []
    if include_ledger_index and ledger.exists():
        for row in list_receipts(ledger, limit=0 if False else 10**9):
            ledger_rows.append({
                "integrity": row.get("integrity"),
                "canonical_hash": row.get("canonical_hash"),
                "timestamp": row.get("timestamp") or row.get("logged_at"),
                "lineage_family": row.get("lineage_family"),
                "lineage_confidence": row.get("lineage_confidence"),
                "hyperstition_risk": row.get("hyperstition_risk"),
                "ingest_source": row.get("ingest_source"),
                "receipt_path": row.get("receipt_path"),
                "observed_preview": (row.get("observed_preview") or "")[:240],
            })

    # Write per-receipt summaries
    written_receipts: List[str] = []
    for i, s in enumerate(summaries):
        integ = s.get("integrity") or f"anon_{i}"
        name = f"{integ}.json"
        (receipts_out / name).write_text(
            json.dumps(s, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written_receipts.append(f"receipts/{name}")

    if ledger_rows:
        ledger_path_out = out / "ledger_index.jsonl"
        with ledger_path_out.open("w", encoding="utf-8") as fh:
            for row in ledger_rows:
                fh.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")

    stats = ledger_stats(ledger) if ledger.exists() else {
        "n_entries": 0,
        "families": {},
        "chain_ok": None,
        "note": "no local ledger",
    }

    index = {
        "schema": "hyperlex.analysis_archive.v1",
        "snapshot_id": snap,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "long_term_ingest_analysis",
        "primary_store": "local ~/.hyperlex (not replaced by this archive)",
        "publish_safe": True,
        "n_receipt_summaries": len(summaries),
        "n_ledger_rows": len(ledger_rows),
        "receipt_files": written_receipts,
        "stats": {
            "n_entries": stats.get("n_entries"),
            "n_with_lineage": stats.get("n_with_lineage"),
            "families": stats.get("families"),
            "hyperstition_stages": stats.get("hyperstition_stages"),
            "ingest_sources": stats.get("ingest_sources"),
            "mean_lineage_confidence": stats.get("mean_lineage_confidence"),
            "chain_ok": stats.get("chain_ok"),
        },
        "summaries": summaries,
    }
    (out / "index.json").write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Markdown for MkDocs / GitHub browsing
    fam_lines = "\n".join(
        f"| {k} | {v} |" for k, v in (stats.get("families") or {}).items()
    ) or "| — | 0 |"
    md = f"""# Analysis archive — `{snap}`

Sanitized export for **long-term ingest analysis**.  
Primary durable store remains local (`~/.hyperlex/`). This bundle is publish-safe
for the docs site / git history.

| Field | Value |
|-------|-------|
| Snapshot | `{snap}` |
| Receipt summaries | {len(summaries)} |
| Ledger rows | {len(ledger_rows)} |
| Chain OK | {stats.get("chain_ok")} |

## Family distribution

| Family | Count |
|--------|------:|
{fam_lines}

## Machine index

- [`index.json`](./index.json) — full snapshot metadata + summaries
- [`ledger_index.jsonl`](./ledger_index.jsonl) — append-friendly ledger extract (if present)
- [`receipts/`](./receipts/) — per-receipt sanitized JSON

## Epistemic notes

- Lineage matches are **INFERRED**
- Virality predictions are **SPECULATIVE**
- Open receipts keep `brier: null` (Brier requires settlement)

Regenerate:

```bash
python3 scripts/hyperlex.py archive-export --out-dir docs/archive/latest
```
"""
    (out / "README.md").write_text(md, encoding="utf-8")
    # MkDocs prefers index.md for directories
    (out / "index.md").write_text(md, encoding="utf-8")

    return {
        "ok": True,
        "snapshot_id": snap,
        "out_dir": str(out),
        "n_receipt_summaries": len(summaries),
        "n_ledger_rows": len(ledger_rows),
        "index": str(out / "index.json"),
    }
