# Cron / LIVE_EMERGENCE_SCAN examples

Advisory job envelopes for Hermes cron. **Never auto-registered** — operator must paste into Hermes or run `hermes cron add`.

| File | Tier | Cadence | Notes |
|------|------|---------|--------|
| `live-emergence-scan.job.json` | MODERATE (default) | every 6h | Baseline mock scan |
| `risk-tier-elevated.job.json` | ELEVATED | every 2h | combined source + vector-seed + archive post-hooks |
| `scan-queries.json` | — | — | Atomic query pack (one term/phrase each) |

Queries are **lexicon atoms** (or true multi-word phrases like `locked in`). Do not bag
independent items into one string.

## Generate from risk

```bash
# Direct tier
python3 scripts/hyperlex.py risk-schedule --tier CRITICAL --schedule-out /tmp/hlx-cron

# From Phase 5 risk on a seed (multi-term bags expand to atomic scan queries)
python3 scripts/hyperlex.py risk-schedule --term "agentic slop" --domain ai --schedule-out /tmp/hlx-cron

# Same via simulate
python3 scripts/hyperlex.py simulate --mode schedule --tier MODERATE --schedule-out /tmp/hlx-cron
```

Policy table (advisory):

| Tier | Cron | Interval | max_queries | source |
|------|------|----------|-------------|--------|
| LOW | `0 */12 * * *` | 12h | 3 | mock |
| MODERATE | `0 */6 * * *` | 6h | 5 | mock |
| ELEVATED | `0 */2 * * *` | 2h | 8 | combined |
| CRITICAL | `0 * * * *` | 1h | 12 | combined |

Post-scan: `scan` summaries include `scan_risk_advisory` (lineage coverage → next tier suggestion).

See `docs/cron-live-emergence.md`.
