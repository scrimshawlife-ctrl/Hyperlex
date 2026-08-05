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

## Fail-closed rules

- Open analysis keeps `provenance.brier = null`
- Empty score series → `NOT_COMPUTABLE`
- Cron script should exit non-zero only on hard failures (import/path); soft source failures degrade
