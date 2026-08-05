# Operator loop (recommended)

After Phase 5.0–5.3 research tooling, the highest-leverage path is **not** more
simulation surface. It is a short **burn-in** that produces settled Brier from
real operator work.

## Posture (current recommendation)

| Do | Defer |
|----|--------|
| Register one MODERATE cron (mock / offline) | ANN vector backend |
| `run` + `pending` + `settle` + `score-series` | More Phase 5 modes |
| Use `scan_risk_advisory` as a signal | Auto-mutating Hermes cron |
| Bump tier only after evidence | Public PyPI / Abraxas hard import |

ANN is optional until the local vector corpus is large enough that linear cosine
hurts. Doctor-scale (~hundreds of terms) does not need it.

## Daily path (simplified)

```bash
export HERMES_SKILL_DIR="${HERMES_SKILL_DIR:-$HOME/.hermes/skills/hyperlex}"
HLX="python3 $HERMES_SKILL_DIR/scripts/hyperlex.py"

# See the map anytime
$HLX commands

# One-shot: ingest route → analyze → receipt → forecasts → score log
$HLX run "rizz" --route offline
$HLX run "locked in" --route offline

# Multi-query cron shape (atomic pack; offline-safe)
$HLX scan --config "$HERMES_SKILL_DIR/examples/cron/scan-queries.json" \
  --route offline --receipt --forecasts --append-log

# When network is allowed
$HLX run "agentic slop" --route live
```

### Ingest routing (prefer routes over adapter names)

| Route | Resolves to | Network |
|-------|-------------|---------|
| `offline` / `mock` / `default` | `mock` | no |
| `live` | `combined` | yes |
| `glossary` | `glossary` | yes |
| `social` | `x_search` | yes |

Aliases still work (`real`→glossary, `x`→x_search, `firecrawl`→crawl4ai).
`HYPERLEX_OFFLINE=1` forces mock for any network source.

```bash
$HLX sources
$HLX sources --route live          # preview resolve
$HLX ingest "rizz" --route offline
$HLX analyze "rizz" --route offline
```

## Calibration path (where Brier appears)

```bash
$HLX pending                       # open forecasts in score log
$HLX settle --forecast-id <id> --decision TRUE   # or FALSE / VOID
$HLX score-series --mean-shift --verify-chain
```

Rules:

- Open analysis always has `provenance.brier = null`
- Empty series → `NOT_COMPUTABLE`
- Never invent Brier from Phase 5 or scan advisories

## Cron / risk tier (advisory)

```bash
$HLX risk-schedule --tier MODERATE --schedule-out /tmp/hlx-cron
# Operator pastes job into Hermes — Hyperlex never auto-registers
```

Scan summaries include `scan_risk_advisory` (lineage coverage → suggested next
cadence). Re-run `risk-schedule` before changing live jobs.

See [cron-live-emergence.md](cron-live-emergence.md).

## Week-one checklist

1. Install skill: `bash install.sh`
2. `$HLX doctor` green
3. Daily: `$HLX run "…" --route offline` (or MODERATE cron)
4. Settle a handful of forecasts via `pending` → `settle`
5. `$HLX score-series --verify-chain` — first real Brier series
6. Only then: `--route live` or ELEVATED/CRITICAL tiers if advisory warrants

## Command map

Full simplified map: [commands.md](commands.md) or `$HLX commands`.
