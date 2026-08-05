# Analysis archive — `post-backfill-0.2.12`

Sanitized export for **long-term ingest analysis**.  
Primary durable store remains local (`~/.hyperlex/`). This bundle is publish-safe
for the docs site / git history.

| Field | Value |
|-------|-------|
| Snapshot | `post-backfill-0.2.12` |
| Receipt summaries | 9 |
| Ledger rows | 5 |
| Chain OK | True |

## Family distribution

| Family | Count |
|--------|------:|
| betting-sharp | 5 |

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
