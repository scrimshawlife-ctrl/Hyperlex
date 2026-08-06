# Hyperlex as a Hermes skill

## Principle

Hyperlex is a **Hermes skill** implemented as a **Python package repository**.
Once installed, the skill tree is self-contained: automatic pipeline (ingest → results),
receipts, forecasts, settlement, Brier scoring, lineage, Phase 5 research, and vector DB
all run from the skill directory without Abraxas.

Abraxas (or any other host) is an **optional consumer**. Relevant Abraxas wire
shapes are pure Hyperlex modules under `hyperlex.compat.abraxas` — Hyperlex never
imports Abraxas.

```text
┌──────────────────────────────────────────────┐
│  Hyperlex Hermes skill                       │
│  SKILL.md · install.sh · scripts/hyperlex.py │
│  src/hyperlex/ (package)                     │
│  pipeline: ingest → full results             │
│  compat.abraxas (wire shapes only)           │
└──────────────────┬───────────────────────────┘
                   │ optional hand-off
                   ▼
         Hermes host / Abraxas / other
```

## Install

```bash
bash install.sh --dry-run
bash install.sh
export HERMES_SKILL_DIR="${HOME}/.hermes/skills/hyperlex"
export HLX="python3 $HERMES_SKILL_DIR/scripts/hyperlex.py"
$HLX check && $HLX doctor && $HLX commands
```

## Preferred path (automatic backend)

See [operator-loop.md](operator-loop.md) and [commands.md](commands.md).

```bash
# One command → full results (receipt, forecasts, phase5 risk)
$HLX pipeline "rizz" --route offline
# aliases:
$HLX run "rizz"
$HLX ingest "rizz"              # full results; --raw-only = signal only

# Multi-term input expands to separate atoms
$HLX pipeline "sigma rizz locked in"
# → sigma | rizz | locked in  (not one blended seed)

# Only manual calibration step:
$HLX pending
$HLX settle --forecast-id <id> --decision TRUE
$HLX score-series --mean-shift --verify-chain
```

```text
pipeline / run / ingest
  → analyze → receipt → forecasts → score log → phase5 risk
  → pending → settle → score-series   # Brier only here
```

Routes: prefer `--route offline|live|glossary|social` over raw adapter names.

## Run modes

| Mode | How |
|------|-----|
| Hermes skill CLI | `python3 $HERMES_SKILL_DIR/scripts/hyperlex.py …` |
| Package (dev) | `PYTHONPATH=src python -m hyperlex …` |
| Library | `from hyperlex import run_pipeline` |
| Cron | `examples/cron/live-emergence-scan.job.json` |

## Library

```python
from hyperlex import run_pipeline

# Free-text bag is input only — expands to atoms
packet = run_pipeline("sigma rizz locked in", route="offline")
assert packet["atoms"] == ["sigma", "rizz", "locked in"]
assert packet["n_atoms"] == 3
assert packet["brier"] is None
# packet["results"][i] is one full unit per atom
```

## Phase 5 (research)

```bash
$HLX simulate --term rizz --mode scenario --domain ai
$HLX simulate --term "sigma rizz locked in" --domain ai   # multi-term expand
```

All Phase 5 output is **SPECULATIVE** with `brier: null`.  
Demos: [demos/atomic-terms.md](demos/atomic-terms.md).

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

1. Open analysis / pipeline: `provenance.brier is null`
2. Unsettled series: `NOT_COMPUTABLE`
3. Operator review never includes `autonomous_reliability_mutation` or `execute_production`
4. No network required for `route=offline` / `source=mock`
5. Multi-term free text expands to atoms — never density-stacked as one primary seed by default

## Operator data locations

```text
~/.hyperlex/receipts/
~/.hyperlex/receipt_ledger.jsonl
~/.hyperlex/score_log.jsonl
~/.hyperlex/cache/
~/.hyperlex/vector.db              # SQLite vector store (default)
~/.hyperlex/chroma/                # local Chroma persist (opt-in)
~/.hyperlex/rate_limit.json
~/.hermes/.env                     # CHROMA_* / HYPERLEX_CHROMA_* secrets (auto-loaded)
```

Vector map: [modules/vectordb.md](modules/vectordb.md).
