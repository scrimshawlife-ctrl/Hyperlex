# Run snapshot — `golden-seed-0.3.2`

**Kind:** `analysis` · **Publish-safe static history** for GitHub Pages.

Primary durable store remains local (`~/.hyperlex/`). This bundle is sanitized
for the docs site / git history — not a replacement for the operator ledger.

| Field | Value |
|-------|-------|
| Snapshot | `golden-seed-0.3.2` |
| Kind | `analysis` |
| Receipt summaries | 9 |
| Ledger rows | 5 |
| Chain OK | True |

## Family distribution

| Family | Count |
|--------|------:|
| ai-native | 1 |
| betting-sharp | 1 |
| brainrot-aura | 1 |
| crypto-degen | 1 |
| gaming-meta | 1 |
| kinship-address | 1 |
| (none) | 1 |
| political-status | 1 |
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
