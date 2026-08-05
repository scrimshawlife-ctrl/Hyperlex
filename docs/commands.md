# Command map (simplified)

Hyperlex has many subcommands. Prefer this map. Full list: `$HLX commands` (JSON)
or `python3 scripts/hyperlex.py -h`.

```bash
HLX="python3 ${HERMES_SKILL_DIR:-$HOME/.hermes/skills/hyperlex}/scripts/hyperlex.py"
```

## Daily ops

| Command | Purpose |
|---------|---------|
| `run "<query>"` | One-shot: analyze + receipt + forecasts + append score log |
| `run "<query>" --route offline` | Safe burn-in (default route for `run`) |
| `run "<query>" --route live` | Network multi-source when allowed |
| `scan --route offline --receipt --forecasts --append-log` | Multi-query LIVE_EMERGENCE_SCAN |
| `risk-schedule --tier MODERATE --schedule-out DIR` | Advisory Hermes cron envelope |

## Calibration

| Command | Purpose |
|---------|---------|
| `pending` | Open (unsettled) forecasts from score log |
| `settle --forecast-id ID --decision TRUE\|FALSE\|VOID` | Operator settlement |
| `score-series --mean-shift --verify-chain` | Brier series from settled pairs |

## Ingest routing

| Command | Purpose |
|---------|---------|
| `sources` | Catalog + named routes |
| `sources --route live` | Preview resolve |
| `ingest "<query>" --route offline` | Ingest only (structured fingerprint) |
| `analyze "<query>" --route offline` | Analyze without auto-receipt |

Prefer **`--route offline|live|glossary|social`** over raw adapter names.
Aliases: `real`→glossary, `x`→x_search, `firecrawl`→crawl4ai, `live`→combined.

## Research (SPECULATIVE · brier null)

| Command | Purpose |
|---------|---------|
| `simulate --term T --mode scenario` | Phase 5 composed scenario |
| `simulate --mode schedule --tier ELEVATED` | Risk→scan plan |
| `vector-search "…"` | Local vector DB |
| `archive-export --history` | Sanitized Pages run history |

## Maintenance

| Command | Purpose |
|---------|---------|
| `doctor` / `check` / `smoke` | Health |
| `list-receipts` / `ledger-stats` | Local ledger |
| `commands` | Print this map as JSON |

## Pipeline shape

```text
--route offline|live
       ↓
   ingest  →  analyze  →  receipt + forecasts
       ↓                      ↓
   (fingerprint)         score log → pending → settle → score-series
                              ↓
                    scan / risk-schedule (cron advisory)
```

## Deferred (do not prioritize)

- ANN vector backend (until corpus is large)
- More Phase 5 modes
- Public PyPI; Abraxas hard dependency
