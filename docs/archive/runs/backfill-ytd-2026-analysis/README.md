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

| Family | Count | Map |
|--------|------:|-----|
| `brainrot-aura` | 5 | [map](../../../map/index.md?family=brainrot-aura) |
| `ai-native` | 3 | [map](../../../map/index.md?family=ai-native) |
| `betting-sharp` | 2 | [map](../../../map/index.md?family=betting-sharp) |
| `gaming-meta` | 2 | [map](../../../map/index.md?family=gaming-meta) |
| `political-status` | 1 | [map](../../../map/index.md?family=political-status) |
| `crypto-degen` | 1 | [map](../../../map/index.md?family=crypto-degen) |
| `kinship-address` | 1 | [map](../../../map/index.md?family=kinship-address) |
| `workplace-corp` | 1 | [map](../../../map/index.md?family=workplace-corp) |

Open the [slang lineage map](../../../map/index.md) for the full constellation.

## Machine index

- [`index.json`](./index.json) — full snapshot metadata + summaries
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

Back to [run history catalog](../../index.md) · [Slang map](../../../map/index.md).
