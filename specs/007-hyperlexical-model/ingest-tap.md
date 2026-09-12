# Spec 007 — live ingest tap (SHADOW)

**Product voice:** **ne0l0gist** ingest. Writes candidates for the **Hyperlexical** train/eval path. `name_gate` stays false.

**Date**: 2026-09-10  
**Lane**: SHADOW / advisory  
**Does not open**: API_V1, T13 promote, Hub, Brier, OBSERVED promotion

## Intent

Current slang ingest already runs `pipeline` / `analyze` / `scan` / `relay --push-inbox`.
Those atoms were not entering the Hyperlexical dataset. This **ne0l0gist** tap writes them into a
local candidate store so T1 harvest can use *current* data without copying
`~/.hyperlex` ledgers into git.

## Contract

| Field | Rule |
|---|---|
| class | always `INFERRED` |
| brier | always null |
| forecast_eligible | false (not on the row) |
| provenance | `ingest:{pipeline\|scan\|inbox\|store}` — no home paths |
| restricted | drop surface; do not write the row |
| name-gate | never true from this tap alone |
| git | store is local only |

## Surfaces

1. `pipeline.run_one` fail-open after analyze
2. `python -m hyperlex analyze|scan` fail-open
3. CLI: `PYTHONPATH=scripts/shadow python3 -m hyperlexical.ingest_tap --from-json packet.json`
4. Inbox harvest: `~/.hyperlex/signals/inbox.jsonl`
5. Optional export merge: `python3 -m hyperlexical.export --include-live`

## Store

`~/.hyperlex/hyperlexical/ingest_candidates.jsonl`  
Override: `HYPERLEX_HYPERLEXICAL_STORE`

Operator stamp **2026-09-10 PT evening**: **4333** rows (402 OBSERVED / 3931 INFERRED). Local-only. Not the 883-row tracked seed.

## Operator loop

```text
pipeline "rizz" --route offline
  → analyze
  → tap writes INFERRED candidate
  → pending → settle (receipts stay receipts)
  → PYTHONPATH=scripts/shadow python3 -m hyperlexical.ingest_tap --inbox ~/.hyperlex/signals/inbox.jsonl
  → PYTHONPATH=scripts/shadow python3 -m hyperlexical.export --include-live
```

Operator settlement of a *forecast* does not auto-promote a dataset row to OBSERVED.
A dataset row becomes OBSERVED only after an explicit harvest settlement.

## Notion

Operator page minted 2026-09-10 under 02 Operator.
Spine Owner overlay updated. Vernacular Intelligence cross-link updated.
