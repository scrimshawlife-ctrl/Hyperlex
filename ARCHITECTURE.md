# Hyperlex Architecture

**Version:** 0.2.x · **Mode:** Hermes skill (Python package repo)

Hyperlex is a pure-function-first memetic engine packaged as a Hermes skill.
Optional append-only side effects: receipts, score log, receipt ledger.
It does **not** import Abraxas. Relevant Abraxas wire shapes live under `hyperlex.compat.abraxas`.

## Data flow

```
query + source
    → intake (cache, rate limit, fingerprints)
    → analysis (neologism, lineage, virality, memetics, hyperstition)
    → optional: extract_forecasts (no Brier)
    → optional: emit_receipt + receipt ledger
    → optional: relay RUNE.HLX.* envelopes
    → time / operator settlement
    → score_pair / score_series (Brier only if settled)
    → optional: market_signal / forecast_pipeline connectors
    → optional: hyperstition feedback → future mapping advice
```

## Package layout

```
src/hyperlex/
  intake/           # ingest adapters + cache + glossaries + x_search
  analysis/         # memetic core + lineage matcher
  synthesis/        # external signal stub
  receipt/          # emit + hash-chained receipt ledger
  calibration/      # forecast, settle, score, score_log, recalibrate
  relay/            # RUNE.HLX.* envelopes
  connectors/       # market-signal + forecast pipeline packets (generic)
  diagrams/         # Mermaid from receipts / ledger
  compat/abraxas/   # BrierLedger/Score/operator review/claims/runes (no Abraxas import)
  provenance.py     # source fingerprints
  cli.py            # python -m hyperlex
  schemas/          # package-local JSON schemas
```

## Layers

### 1. Intake
| Source | Role |
|--------|------|
| `mock` | Deterministic, query-aware offline |
| `glossary` / `real` / `web` | Action Network |
| `glossary_expanded` | Multi-glossary pack |
| `reddit`, `urban`, `wikipedia` | Live public APIs |
| `x_search` | Bearer API → xurl → stub |
| `crawl4ai` / `firecrawl` | Web crawl |
| `combined` | Ordered multi-source merge |

Disk cache: `~/.hyperlex/cache/` · Rate limits: `~/.hyperlex/rate_limit.json`

### 2. Analysis
- Neologisms, semantic variation, virality hybrid, memetics protocol, hyperstition stage
- Lineage match + confidence (`≥ 0.42`) with transparent `score_breakdown`
- Open results: `provenance.brier = null` always

### 3. Calibration
- Signal→f maps (lineage, virality, hyperstition stage)
- Settlement → atomic/series Brier, Murphy, Ferro–Fricker, Yates, Vieira, Δf
- Score log: `~/.hyperlex/score_log.jsonl`
- Hyperstition feedback: advisory stage-map updates from settled series (future forecasts only)

### 4. Receipts & ledgers
- Receipt files: `~/.hyperlex/receipts/`
- Receipt ledger: `~/.hyperlex/receipt_ledger.jsonl` (hash-chained index)

### 5. Relay & connectors
- `relay` → `RUNE.HLX.LIVE_EMERGENCE_SCAN`, `COMMUNICATION_RELAY`, `CALIBRATION_*`
- `connectors.market_signal` → generic market/narrative signal packet
- `connectors.forecast_pipeline` → handoff pack for external forecast systems

### 6. Host compatibility (optional)
Hosts import **from Hyperlex**:

```python
from hyperlex.compat.abraxas import (
    to_brier_ledger_entry,
    to_brier_score_packet,
    to_operator_brier_review,
    list_hlx_runes,
)
```

## Constraints
- No fabricated Brier without settlement
- Fail-closed `NOT_COMPUTABLE`
- OBSERVED / INFERRED / SPECULATIVE discipline
- Python ≥ 3.10, stdlib-first baseline

See [SPEC.md](./SPEC.md), [docs/api-v1.md](./docs/api-v1.md), [docs/hermes-skill.md](./docs/hermes-skill.md).
