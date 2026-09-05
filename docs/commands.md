# Command map (simplified)

Hyperlex has many subcommands. Prefer this map. Full list: `$HLX commands` (JSON)
or `python3 scripts/hyperlex.py -h`.

```bash
HLX="python3 ${HERMES_SKILL_DIR:-$HOME/.hermes/skills/hyperlex}/scripts/hyperlex.py"
```

## Daily ops (automatic backend)

| Command | Purpose |
|---------|---------|
| `wizard [--auto]` | **Week-one guided path** (doctor→demo→pipeline→calibration coach) |
| `demo` | **First success:** offline mock pipeline + receipt (`brier` null) |
| `pipeline "<q>"` | **AUTO:** ingest→analyze→receipt→forecasts→score log→phase5 risk |
| `ingest "<q>"` | Same as pipeline by default (`--raw-only` = signal only) |
| `run "<q>"` | Alias of pipeline |
| `pipeline "sigma rizz locked in"` | Auto-expands to atoms; full results each |
| `terms-split "…"` | Preview multi-term expansion only |
| `scan --route offline …` | Multi-query LIVE_EMERGENCE_SCAN |
| `risk-schedule --tier MODERATE --schedule-out DIR` | Advisory Hermes cron envelope |

```text
pipeline / run / ingest
        |
        v
   resolve route → expand atoms → for each atom:
        analyze → receipt → forecasts → score_log → phase5 risk
        |
        v
   results packet (brier always null until settle)
```

## Calibration

| Command | Purpose |
|---------|---------|
| `pending` | Open (unsettled) forecasts from the score log |
| `settle --forecast-id ID --decision TRUE\|FALSE\|VOID` | Operator settlement |
| `score-series --mean-shift --verify-chain` | Brier series from settled pairs |

## Ingest routing

| Command | Purpose |
|---------|---------|
| `sources` | Catalog + named routes |
| `sources --route live` | Preview resolve |
| `ingest "<query>" --route offline` | Ingest only (structured + fingerprint) |
| `analyze "<query>" --route offline` | Analyze without auto-receipt |

Prefer **`--route offline|live|glossary|social`** over raw adapter names.
Aliases: `real`→glossary, `x`→x_search, `firecrawl`→crawl4ai, `live`→combined.

## Research (SPECULATIVE · brier null)

| Command | Purpose |
|---------|---------|
| `simulate --term T --mode scenario` | Phase 5 composed scenario |
| `simulate --mode schedule --tier ELEVATED` | Risk→scan plan |
| `mutation trace "it's giving mid rizz"` | Detect operator stacks (brier null · forecast_eligible false) |
| `mutation predict "rizz"` | Next civilian surfaces (SPECULATIVE · brier null) |
| `mutation-predict "rizz"` | Deprecated alias of `mutation predict` |
| `archive-export --history` | Sanitized Pages run history |

## Vector DB (sqlite · local chroma · cloud)

| Command | Purpose |
|---------|---------|
| `vector-seed --backend chroma --db ~/.hyperlex/chroma --through 2026-08 --include-home --include-golden` | **Backfill local Chroma** (registry + packs + receipts) |
| `vector-seed --through 2026-08 --include-home` | Same into default SQLite |
| `vector-stats --backend chroma --db ~/.hyperlex/chroma` | Local Chroma counts |
| `vector-stats --cloud` | Chroma Cloud counts |
| `vector-search "…" --backend chroma --db ~/.hyperlex/chroma --kind term` | Search local Chroma |
| `vector-sync --from-path ~/.hyperlex/chroma --to cloud` | **Promote** local → Cloud (no re-embed) |
| `vector-export -o file.jsonl` | Dump embeddings JSONL |
| `vector-import -i file.jsonl [--cloud]` | Load dump |

Flow: **seed local → search → sync to cloud**. Secrets: `~/.hermes/.env` (`CHROMA_API_KEY`, …).
Docs: [modules/vectordb.md](modules/vectordb.md).

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

`analyze` / `pipeline` attach `analysis.mutation_trace` when operators fire.

## Deferred (do not prioritize)

- Multi-collection / remote embed models beyond hash default
- More Phase 5 modes
- Public PyPI; Abraxas hard dependency
