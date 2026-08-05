# Hyperlex as a Hermes skill (Python package repo)

## Principle

Hyperlex is a **Hermes skill** implemented as a **Python package repository**.
Once installed, the skill tree is self-contained: analysis, receipts, forecasts,
settlement, Brier scoring, score logs, diagrams, and HLX rune envelopes all run
from the skill directory without Abraxas.

Abraxas (or any other host) is an **optional consumer**. Relevant Abraxas wire
shapes are pure Hyperlex modules under `hyperlex.compat.abraxas` — Hyperlex never
imports Abraxas.

```text
┌──────────────────────────────────────────────┐
│  Hyperlex Hermes skill                       │
│  SKILL.md · install.sh · scripts/hyperlex.py │
│  src/hyperlex/ (package)                     │
│  compat.abraxas (wire shapes only)           │
└──────────────────┬───────────────────────────┘
                   │ optional hand-off
                   ▼
         Hermes host / Abraxas / other
         (may import hyperlex modules)
```

## Install

```bash
bash install.sh --dry-run
bash install.sh
# → ~/.hermes/skills/hyperlex
export HERMES_SKILL_DIR="${HOME}/.hermes/skills/hyperlex"
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" check
```

## Run modes

| Mode | How |
|------|-----|
| Hermes skill CLI | `python3 $HERMES_SKILL_DIR/scripts/hyperlex.py …` |
| Package (dev) | `PYTHONPATH=src python -m hyperlex …` |
| Library | `import hyperlex` from skill `src/` or editable install |
| Cron | `examples/cron/live-emergence-scan.job.json` |

## Relevant Abraxas capabilities (as Hyperlex modules)

| Capability | Hyperlex module | Wire schema |
|------------|-----------------|-------------|
| Claim labels | `compat.abraxas.claims` | OBSERVED / INFERRED / SPECULATIVE / NOT_COMPUTABLE |
| Brier atomic score packet | `compat.abraxas.brier_score` | `BrierScorePacket.v1` |
| Brier ledger entry | `compat.abraxas.brier_ledger` | `BrierLedgerEntry.v1` |
| Operator Brier review | `compat.abraxas.operator_review` | `OperatorBrierReviewPacket.v1` |
| Rune envelopes | `compat.abraxas.runes` + `relay` | `hyperlex.rune_envelope.v1` |

**Not imported:** Abraxas runtime, YGGDRASIL, live Alembic runes, MCP, production execution.

## Fail-closed rules (skill-wide)

1. Open analysis: `provenance.brier is null`
2. Unsettled series: `NOT_COMPUTABLE`
3. Operator review never includes `autonomous_reliability_mutation` or `execute_production`
4. No network required for `source=mock`

## Operator data locations

```text
~/.hyperlex/receipts/
~/.hyperlex/receipt_ledger.jsonl
~/.hyperlex/score_log.jsonl
~/.hyperlex/cache/
~/.hyperlex/rate_limit.json
```
