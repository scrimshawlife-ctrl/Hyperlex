# Hyperlex as a standalone app

## Principle

Hyperlex runs alone. All memetic analysis, receipts, forecasts, settlement,
Brier scoring, score logs, and HLX rune envelopes are self-contained.

Abraxas (or any other host) is an **optional consumer**. Relevant Abraxas
capabilities that Hyperlex needs for interoperability are implemented as
**Hyperlex modules** under `hyperlex.compat.abraxas` — not by importing Abraxas.

```text
┌─────────────────────────────────────────┐
│  Hyperlex (standalone)                  │
│  intake / analysis / receipt / calib    │
│  relay (RUNE.HLX.*)                     │
│  compat.abraxas (wire shapes only)      │
└──────────────────┬──────────────────────┘
                   │ optional hand-off
                   ▼
         Abraxas / Hermes / other host
         (imports hyperlex modules if needed)
```

## Run modes

| Mode | How |
|------|-----|
| Hermes skill | `bash install.sh` → `~/.hermes/skills/hyperlex` |
| Package CLI | `python -m hyperlex …` |
| Library | `import hyperlex` |
| Cron | `examples/cron/live-emergence-scan.job.json` |

## Relevant Abraxas capabilities (as Hyperlex modules)

| Capability | Hyperlex module | Wire schema |
|------------|-----------------|-------------|
| Claim labels | `compat.abraxas.claims` | OBSERVED / INFERRED / SPECULATIVE / NOT_COMPUTABLE |
| Brier atomic score packet | `compat.abraxas.brier_score` | `BrierScorePacket.v1` |
| Brier ledger entry | `compat.abraxas.brier_ledger` | `BrierLedgerEntry.v1` |
| Operator Brier review | `compat.abraxas.operator_review` | `OperatorBrierReviewPacket.v1` |
| Rune envelopes | `compat.abraxas.runes` + `relay` | `hyperlex.rune_envelope.v1` |

**Not imported / not reimplemented:** Abraxas runtime, YGGDRASIL, live Alembic
runes, MCP, governance Authority pydantic models, production execution paths.

## Fail-closed rules (app-wide)

1. Open analysis: `provenance.brier is null`
2. Unsettled series: `NOT_COMPUTABLE`
3. Operator review never includes `autonomous_reliability_mutation` or `execute_production`
4. No network required for `source=mock`

## Data locations

```text
~/.hyperlex/receipts/           # receipt JSON files
~/.hyperlex/receipt_ledger.jsonl
~/.hyperlex/score_log.jsonl
~/.hyperlex/cache/
~/.hyperlex/rate_limit.json
```
