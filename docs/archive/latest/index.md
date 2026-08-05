# Run snapshot — `backfill-ytd-2026-analysis`

**Kind:** `analysis` · **Publish-safe static history** for GitHub Pages.

Primary durable store remains local (`~/.hyperlex/`). This bundle is sanitized
for the docs site / git history — not a replacement for the operator ledger.

| Field | Value |
|-------|-------|
| Snapshot | `backfill-ytd-2026-analysis` |
| Kind | `analysis` |
| Receipt summaries | 16 |
| Ledger rows | 0 |
| Chain OK | True |

## Family distribution

| Family | Count |
|--------|------:|
| brainrot-aura | 5 |
| ai-native | 3 |
| betting-sharp | 2 |
| gaming-meta | 2 |
| political-status | 1 |
| crypto-degen | 1 |
| kinship-address | 1 |
| workplace-corp | 1 |

## Machine index

- [`index.json`](./index.json) — full snapshot metadata + summaries
- [`ledger_index.jsonl`](./ledger_index.jsonl) — ledger extract (if present)
- `receipts/` — per-receipt sanitized JSON (JSON files; browse via index)

## Epistemic notes

- Lineage matches are **INFERRED**
- Virality predictions are **SPECULATIVE**
- Open receipts keep `brier: null` (Brier requires settlement)
- This Pages snapshot is a **static history of runs**, not live state

Regenerate / append history:

```bash
python3 scripts/hyperlex.py archive-export --include-golden --history
```

Back to [run history catalog](../../index.md).
