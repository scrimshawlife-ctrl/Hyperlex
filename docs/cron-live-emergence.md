# LIVE_EMERGENCE_SCAN — Hermes cron

## Intent

Run Hyperlex on a fixed query pack every N hours, emit receipts + forecasts,
append the receipt ledger and score log. **Never invent Brier** — operators
settle later via `settle` / `score-series`.

## Prerequisites

```bash
bash install.sh   # ~/.hermes/skills/hyperlex
export HERMES_SKILL_DIR="$HOME/.hermes/skills/hyperlex"
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" check
```

## One-shot (manual)

```bash
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" scan \
  --config "$HERMES_SKILL_DIR/examples/cron/scan-queries.json" \
  --source mock \
  --receipt --forecasts --append-log \
  --json
```

## Hermes cron job

Template: `examples/cron/live-emergence-scan.job.json`

| Field | Value |
|-------|--------|
| name | `hyperlex-live-emergence-scan` |
| skills | `["hyperlex"]` |
| no_agent | `true` (script is the whole job) |
| schedule | `0 */6 * * *` (every 6h) |
| script | see job JSON |

Register (example CLI shape — adapt to your Hermes version):

```bash
hermes cron add \
  --name "hyperlex-live-emergence-scan" \
  --cron "0 */6 * * *" \
  --skill hyperlex \
  --no-agent \
  --script 'export HERMES_SKILL_DIR="$HOME/.hermes/skills/hyperlex"; python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" scan --config "$HERMES_SKILL_DIR/examples/cron/scan-queries.json" --source mock --receipt --forecasts --append-log --json'
```

Or paste fields from the job JSON into the Hermes UI / `cron/jobs.json` carefully.

## Outputs

| Artifact | Path |
|----------|------|
| Receipts | `~/.hyperlex/receipts/hyperlex_*.json` |
| Receipt ledger | `~/.hyperlex/receipt_ledger.jsonl` |
| Forecast score log | `~/.hyperlex/score_log.jsonl` |
| Scan summary JSON | stdout (+ optional `--out`) |

## Operator settle loop

```bash
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" list-receipts --limit 10
# settle forecasts from score log
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" settle --forecast-id <id> --decision TRUE
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" score-series --mean-shift --verify-chain
```

## Network mode

Replace `--source mock` with `combined` or `glossary` only when:

- network is allowed
- optional deps installed if using crawl4ai
- rate limits / disk cache are acceptable (`~/.hyperlex/cache/`)

Offline safety: `HYPERLEX_OFFLINE=1` forces non-network fallbacks.

## Risk-tier → schedule coupling (advisory · v0.3.7)

Maps hyperstition risk tiers to recommended scan cadence. **Does not** auto-mutate
Hermes cron — operator reviews and registers.

| Tier | Cron | Interval | max_queries | source | post-hooks |
|------|------|----------|-------------|--------|------------|
| LOW | `0 */12 * * *` | 12h | 3 | mock | — |
| MODERATE | `0 */6 * * *` | 6h | 5 | mock | — |
| ELEVATED | `0 */2 * * *` | 2h | 8 | combined | vector-seed + archive-export |
| CRITICAL | `0 * * * *` | 1h | 12 | combined | vector-seed + archive-export |

```bash
# List policy
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" risk-schedule --list-tiers

# Direct tier → write job envelope
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" risk-schedule \
  --tier ELEVATED --schedule-out /tmp/hlx-cron

# From seed term (Phase 5 risk)
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" risk-schedule \
  --term "agentic slop skill issue" --domain ai --schedule-out /tmp/hlx-cron

# Equivalent simulate mode
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" simulate --mode schedule --tier CRITICAL
```

Example envelopes: `examples/cron/risk-tier-elevated.job.json`,
`examples/cron/live-emergence-scan.job.json` (MODERATE default).

### Post-scan advisory

Every `scan` summary includes `scan_risk_advisory` (lineage coverage → suggested next
tier / cron). Re-run `risk-schedule` for full Phase 5 risk before changing live jobs.

## Fail-closed rules

- Open analysis keeps `provenance.brier = null`
- Empty score series → `NOT_COMPUTABLE`
- Cron script should exit non-zero only on hard failures (import/path); soft source failures degrade
- Risk→schedule plans keep `brier: null` and `state: proposed`
