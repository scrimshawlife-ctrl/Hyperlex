<p align="center">
  <img src="assets/hyperlex-imagine-hero.jpg" alt="Hyperlex — memetic emergence (Grok Imagine)" width="360">
</p>
<p align="center">
  <sub>Visual identity · <a href="https://grok.com/imagine/post/0fef2df1-6bec-4b18-9ee6-823dd77ba9f6">Grok Imagine</a></sub>
</p>

# Hyperlex

**Memetic emergence engine as a Hermes skill** — detect slang and cultural signals, match lineage, score virality and hyperstition, emit auditable receipts, and run **settled** Brier calibration. Optional Phase 5 research simulation. Optional Abraxas-compatible wire shapes (import *from* Hyperlex; never import Abraxas).

| | |
|--|--|
| **Version** | **0.3.8** |
| **Posture** | Hermes skill · Python package repo (≥3.10) · MIT |
| **Phases** | **0–4 complete** · **5.0–5.3** research + operator loop |
| **Pages** | Static history of runs (not live operator DB) |
| **PyPI** | Not planned (local / Hermes install only) |

**Docs site:** https://scrimshawlife-ctrl.github.io/Hyperlex/ · [telemetry desk](https://scrimshawlife-ctrl.github.io/Hyperlex/telemetry/) · [operator loop](https://scrimshawlife-ctrl.github.io/Hyperlex/operator-loop/)  
**Status:** [STATUS.md](./STATUS.md) · **Skill contract:** [SKILL.md](./SKILL.md)

---

## What it does

Hyperlex answers: *what is emerging in language/culture, which family does it belong to, how viral/hyperstitious is it, and can we score forecasts only after real outcomes?*

```text
run --route offline|live
  → receipt + forecasts → score log
  → pending → settle → score-series    # Brier only after settlement
  → optional: scan / risk-schedule / Phase 5 / archive-export
```

| Function | Role |
|----------|------|
| **Ingest** | Routes: `offline` / `live` / `glossary` / `social` (or raw adapters) |
| **Analyze** | Neologisms, lineage (8 families + 2026 YTD leaves), typology, virality (**SPECULATIVE**), hyperstition |
| **Receipts** | Integrity-hashed JSON + append-only local ledger |
| **Calibration** | Forecasts → operator settle → Brier / BSS / Murphy / Yates (never invented) |
| **Scan / cron** | Multi-query `LIVE_EMERGENCE_SCAN` + advisory risk→schedule plans |
| **Phase 5** | Transmission, multi-agent, risk tiers, phylogeny, research export (**SPECULATIVE**) |
| **Vector DB** | Local SQLite at `~/.hyperlex/vector.db` |
| **Pages archive** | Sanitized dated run history under `docs/archive/runs/` |

### Hard rules

1. **Brier requires settlement** — open analysis always has `provenance.brier = null`.
2. **Phase 5 is SPECULATIVE** — simulation packets also keep `brier: null`.
3. **No Abraxas hard import** — `hyperlex.compat.abraxas` is pure Hyperlex wire shapes.
4. **Primary store is local** — `~/.hyperlex/`. Pages is sanitized history only.
5. **Cron is advisory** — `risk-schedule` never auto-registers Hermes jobs.

---

## How to use

### 1. Install

```bash
bash install.sh --dry-run && bash install.sh
export HERMES_SKILL_DIR="${HOME}/.hermes/skills/hyperlex"
export HLX="python3 $HERMES_SKILL_DIR/scripts/hyperlex.py"

$HLX check
$HLX doctor
$HLX smoke
$HLX commands    # simplified command map (JSON)
```

Optional editable package:

```bash
pip install -e ".[dev]"
python -m hyperlex check
python -m hyperlex run "sharp steam" --route offline
```

### 2. Daily path (recommended)

One-shot: **ingest route → analyze → receipt → forecasts → score log**.

```bash
# Safe offline burn-in (default route for `run` is offline)
$HLX run "sharp steam revenge" --route offline

# When network is allowed
$HLX run "agentic slop skill issue" --route live

# Analyze only (no auto receipt / forecasts)
$HLX analyze "rizz locked in" --route offline
$HLX ingest "rizz locked in" --route offline
```

### 3. Ingest routes (prefer these over raw adapters)

| Route | Resolves to | Network |
|-------|-------------|---------|
| `offline` / `mock` / `default` | `mock` | no |
| `live` | `combined` | yes |
| `glossary` | Action Network glossary | yes |
| `social` | X/Twitter path | yes |

```bash
$HLX sources                 # full catalog + routes
$HLX sources --route live    # preview resolve
```

Aliases still work: `real`→glossary, `x`→x_search, `firecrawl`→crawl4ai.  
Force offline for any network source: `HYPERLEX_OFFLINE=1`.

### 4. Calibration (where Brier appears)

```bash
$HLX pending                                      # open (unsettled) forecasts
$HLX settle --forecast-id <id> --decision TRUE    # or FALSE / VOID / CONFLICT
$HLX score-series --mean-shift --verify-chain
```

Empty series → `NOT_COMPUTABLE`. Never invent scores from open analysis or Phase 5.

### 5. Multi-query scan + advisory cron

```bash
# LIVE_EMERGENCE_SCAN (offline-safe)
$HLX scan \
  --config "$HERMES_SKILL_DIR/examples/cron/scan-queries.json" \
  --route offline --receipt --forecasts --append-log

# Risk tier → Hermes job envelope (operator must register)
$HLX risk-schedule --list-tiers
$HLX risk-schedule --tier MODERATE --schedule-out /tmp/hlx-cron
```

Scan summaries include `scan_risk_advisory` (lineage coverage → next cadence).  
Job templates: `examples/cron/`.

### 6. Research (optional · SPECULATIVE)

```bash
$HLX simulate --term "sigma rizz locked in" --mode scenario --domain ai
$HLX simulate --from-analyze --term "sharp steam revenge" --domain markets
$HLX simulate --mode schedule --tier ELEVATED

$HLX vector-seed --include-golden --through 2026-08
$HLX vector-search "sigma rizz locked in" --kind term

$HLX archive-export --include-golden --history
$HLX lineage-backfill --list --through 2026-08
$HLX lineage-backprop --from-golden
```

### 7. Relay & connectors

```bash
$HLX run "sharp steam revenge" --route offline --out /tmp/hlx.json
# (or analyze --receipt --out …)
$HLX relay --input /tmp/hlx.json --forecasts
$HLX signal --input /tmp/hlx.json
$HLX diagram --from-golden --out-dir out/diagrams
```

### Local data

```text
~/.hyperlex/receipts/
~/.hyperlex/receipt_ledger.jsonl
~/.hyperlex/score_log.jsonl
~/.hyperlex/cache/
~/.hyperlex/vector.db
```

Repo packs: `data/backfill/2026/` · phylogeny: `data/phylogeny/`.

### Week-one checklist

1. Install + `$HLX doctor` green  
2. `$HLX run "…" --route offline` a few times (or MODERATE cron)  
3. `$HLX pending` → settle a handful → `$HLX score-series --verify-chain`  
4. Only then: `--route live` or higher risk tiers if advisory warrants  

Full write-up: [docs/operator-loop.md](./docs/operator-loop.md) · [docs/commands.md](./docs/commands.md)

---

## CLI surface

**Prefer**

| Command | Purpose |
|---------|---------|
| `commands` | Simplified map |
| `run "<q>" --route offline` | Daily one-shot |
| `pending` / `settle` / `score-series` | Calibration |
| `scan` / `risk-schedule` | Cron advisory |
| `sources` / `ingest` / `analyze` | Routing + partial pipeline |

**Also available**

```text
check · doctor · smoke
emit-receipt · list-receipts · ledger-stats · ledger-diff
extract-forecasts · verify-score-log · verify-receipt-ledger
relay · signal · feedback · diagram
lineage-backfill · lineage-backprop
simulate · vector-seed · vector-search · vector-stats
archive-export · archive-catalog
validate · verify-receipt
```

Package entry (subset): `python -m hyperlex …`

---

## Library (frozen API)

```python
from hyperlex import (
    detect_memetic_patterns,
    match_lineage,
    emit_receipt,
    extract_forecasts,
    settle_and_log,
    recompute_series,
    relay_from_result,
    run_phase5_scenario,
    list_sources,
    pick_source,
    export_run_history,
    NOT_COMPUTABLE,
    PKG_VERSION,
)

# Prefer routes via pick_source / ingest_route when scripting
src, _ = pick_source(route="offline")
result = detect_memetic_patterns(
    query="sharp steam revenge",
    ingest_source=src,
    ingest_route="offline",
)
assert result["provenance"]["brier"] is None
```

Frozen symbols: [docs/api-v1.md](./docs/api-v1.md) · `hyperlex.API_V1`  
Extended (additive): simulation, archive, vector, sources, schedule.

Abraxas-shaped modules (optional host import — no Abraxas dependency):

```python
from hyperlex.compat.abraxas import (
    to_brier_ledger_entry,
    to_brier_score_packet,
    to_operator_brier_review,
    list_hlx_runes,
    envelopes_from_result,
)
```

---

## Current status

| Area | Status |
|------|--------|
| Hermes skill + `doctor` | Ready |
| Offline mock + route-based ingest | Ready |
| `run` / `commands` / `pending` | Ready (v0.3.8) |
| Lineage + YTD backfill / backprop | Ready |
| Receipts / ledger / settle / score-series | Ready |
| Risk → scan/cron schedule (advisory) | Ready |
| Phase 5 research simulation | Ready |
| Local vector DB + hybrid lineage | Ready |
| Pages static run history | Ready |
| ANN vector backend | Deferred (corpus still small) |
| Public PyPI | Not planned |

Roadmap: [ROADMAP.md](./ROADMAP.md)

---

## Docs & examples

| Resource | Purpose |
|----------|---------|
| [docs/operator-loop.md](./docs/operator-loop.md) | Recommended burn-in path |
| [docs/commands.md](./docs/commands.md) | Simplified command map |
| [docs/modules/ingest.md](./docs/modules/ingest.md) | Routes, aliases, provenance |
| [docs/cron-live-emergence.md](./docs/cron-live-emergence.md) | Cron / risk tiers |
| [docs/brier-calibration.md](./docs/brier-calibration.md) | Forecast → settle → Brier |
| [docs/phase5.md](./docs/phase5.md) | Research simulation |
| [docs/slang-lineages.md](./docs/slang-lineages.md) | Lineage methodology |
| [docs/hermes-skill.md](./docs/hermes-skill.md) | Skill model + Abraxas boundary |
| [docs site](https://scrimshawlife-ctrl.github.io/Hyperlex/) | Workbench + run history |

Examples:

- `examples/cron/` — LIVE_EMERGENCE_SCAN + risk-tier job envelopes  
- `examples/receipts/golden/` — golden receipt corpus  
- `examples/calibration/` — settled Brier series fixture  
- `examples/slang-families/` — Mermaid lineage diagrams  
- `examples/case-studies/` — end-to-end walkthrough  

---

## License

MIT — see [LICENSE](./LICENSE).
