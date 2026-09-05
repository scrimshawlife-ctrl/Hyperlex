<p align="center">
  <img src="assets/hyperlex-imagine-hero.jpg" alt="Hyperlex — memetic emergence" width="420">
</p>

<h1 align="center">Hyperlex</h1>

<p align="center">
  <strong>Catch language while it’s still becoming culture.</strong><br>
  <em>Hermes skill · memetic emergence engine · settled forecasts only</em>
</p>

<p align="center">
  <a href="https://github.com/scrimshawlife-ctrl/Hyperlex/actions/workflows/hermes-evals.yml"><img src="https://img.shields.io/github/actions/workflow/status/scrimshawlife-ctrl/Hyperlex/hermes-evals.yml?branch=main&label=skill%20ci&logo=github" alt="Skill CI"></a>
  <a href="https://github.com/scrimshawlife-ctrl/Hyperlex/actions/workflows/docs.yml"><img src="https://img.shields.io/github/actions/workflow/status/scrimshawlife-ctrl/Hyperlex/docs.yml?branch=main&label=docs&logo=github" alt="Docs CI"></a>
  <a href="https://scrimshawlife-ctrl.github.io/Hyperlex/"><img src="https://img.shields.io/badge/docs-GitHub%20Pages-0d9488?logo=markdown" alt="Docs"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <a href="./VERSION"><img src="https://img.shields.io/badge/version-0.4.0-informational" alt="Version 0.4.0"></a>
  <img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/hermes-skill-7c3aed" alt="Hermes skill">
  <img src="https://img.shields.io/badge/claude%20code-skill%20%2B%20plugin-d97706" alt="Claude Code">
  <img src="https://img.shields.io/badge/offline--first-mock%20route-22c55e" alt="Offline-first">
  <img src="https://img.shields.io/badge/Brier-settlement%20required-f59e0b" alt="Brier requires settlement">
</p>

<p align="center">
  <a href="https://scrimshawlife-ctrl.github.io/Hyperlex/">Home</a> ·
  <a href="https://scrimshawlife-ctrl.github.io/Hyperlex/start/quickstart/">Quickstart</a> ·
  <a href="https://scrimshawlife-ctrl.github.io/Hyperlex/start/see-it-work/">See it work</a> ·
  <a href="https://scrimshawlife-ctrl.github.io/Hyperlex/commands/">Commands</a> ·
  <a href="https://scrimshawlife-ctrl.github.io/Hyperlex/operator-loop/">Operator loop</a> ·
  <a href="https://scrimshawlife-ctrl.github.io/Hyperlex/archive/">Run history</a> ·
  <a href="./STATUS.md">Status</a>
</p>

<p align="center">
  <sub>Offline first success (no API keys): <code>python3 scripts/hyperlex.py demo</code></sub>
</p>

<p align="center">
  <sub>Visual · <a href="https://grok.com/imagine/post/0fef2df1-6bec-4b18-9ee6-823dd77ba9f6">Grok Imagine</a></sub>
</p>

---

## Plain English

**Hyperlex is a cultural radar for slang.**

New phrases don’t show up fully formed. They leak out of group chats, betting forums, crypto timelines, and AI-native meme stacks — half joke, half signal. Hyperlex watches that fog and asks practical questions:

- What just showed up?
- Which family of slang does it belong to?
- How hard is it spreading?
- Is it just noise, or is it starting to *make itself real* (hyperstition)?
- If we forecast, can we **score ourselves later** — honestly — when the world answers?

It runs as a **Hermes skill**: offline-friendly by default, receipt-backed when you care, and stubborn about one rule — **no fake accuracy**. Brier scores only appear after a human settles an outcome. Simulation stays labeled research. History doesn’t get rewritten.

Cool without the con: less “AI vibe report,” more **flight recorder for memetic weather**.

---

## Atlas

How the pieces sit together:

```text
                    ┌─────────────────────────────────────┐
                    │           HERMES SKILL               │
                    │   SKILL.md · scripts/hyperlex.py     │
                    └─────────────────┬───────────────────┘
                                      │
     ┌────────────────────────────────┼────────────────────────────────┐
     ▼                                ▼                                ▼
┌──────────┐                   ┌────────────┐                   ┌────────────┐
│  INTAKE  │  --route offline  │  ANALYSIS  │                   │  RESEARCH  │
│  routes  │  --route live ──► │  lineage   │                   │  Phase 5   │
│  mock ·  │                   │  virality  │                   │  simulate  │
│  glossary│                   │  hyperstit.│                   │  risk tier │
│  social  │                   └──────┬─────┘                   │  phylogeny │
└──────────┘                          │                         └──────┬─────┘
                                      ▼                                │
                               ┌────────────┐                          │
                               │  RECEIPT   │  hash · ledger           │
                               │  FORECAST  │  p only, no Brier        │
                               └──────┬─────┘                          │
                                      ▼                                │
                               ┌────────────┐     ┌──────────┐         │
                               │  SETTLE    │ ──► │  BRIER   │         │
                               │  operator  │     │  series  │         │
                               └────────────┘     └──────────┘         │
                                      │                                │
                    ┌─────────────────┴────────────────┬───────────────┘
                    ▼                                  ▼
             ~/.hyperlex/                       docs/archive/  (Pages)
             receipts · score log               sanitized run history
             vector.db · cache                  not the live DB
```

| Zone | What lives here |
|------|-----------------|
| **Intake** | Named routes (`offline` / `live` / `glossary` / `social`) — aliases resolve, offline forces mock |
| **Analysis** | Neologisms, 8 lineage families + 2026 YTD leaves, typology, virality, hyperstition stage |
| **Receipt** | Integrity-hashed JSON + append-only ledger under `~/.hyperlex/` |
| **Calibration** | `pending` → `settle` → `score-series` (only place Brier is real) |
| **Scan / cron** | Multi-query `LIVE_EMERGENCE_SCAN` + advisory risk→schedule (never auto-registers) |
| **Research** | Phase 5 transmission, multi-agent, risk, phylogeny — always **SPECULATIVE** |
| **Vector** | SQLite or Chroma (local → Cloud promote) for hybrid lineage re-rank |
| **Pages** | Static, sanitized history — not your operator store |

---

## Why it exists

Most “trend tools” either invent confidence or never close the loop. Hyperlex is built for people who want **both edges**:

1. **Fast sense-making** when a phrase starts climbing  
2. **Slow honesty** when it’s time to score what you claimed  

Phases **0–4** are production skill surface. **5.0–5.3** adds research simulation and operator-loop polish without loosening the settlement rule.

| | |
|--|--|
| **Version** | **0.4.0** |
| **Posture** | Hermes skill · Python package (≥3.10) · MIT |
| **Primary store** | `~/.hyperlex/` |
| **Public PyPI** | Not planned |
| **Abraxas** | Wire shapes only — Hyperlex never imports Abraxas |

---

## Hard rules

1. **Brier requires settlement** — open analysis always has `provenance.brier = null`.  
2. **Phase 5 is SPECULATIVE** — sim packets keep `brier: null`.  
3. **No Abraxas hard dependency** — hosts may import *from* Hyperlex.  
4. **Local is source of truth** — Pages is sanitized history only.  
5. **Cron is advisory** — `risk-schedule` proposes jobs; operators register them.

---

## How to use

### Install

```bash
bash install.sh --dry-run && bash install.sh
export HERMES_SKILL_DIR="${HOME}/.hermes/skills/hyperlex"
export HLX="python3 $HERMES_SKILL_DIR/scripts/hyperlex.py"

$HLX check && $HLX doctor && $HLX smoke
$HLX commands    # simplified map (JSON)
```

Optional: `pip install -e ".[dev]"` then `python -m hyperlex check`.

### Claude Code (additional host)

Hermes stays primary. Claude Code can load the same skill.

```bash
bash install.sh --claude --dry-run && bash install.sh --claude
export HYPERLEX_SKILL_DIR="${HOME}/.claude/skills/hyperlex"
export HLX="python3 $HYPERLEX_SKILL_DIR/scripts/hyperlex.py"
$HLX demo
```

Personal skill: `~/.claude/skills/hyperlex`. Local plugin tree:
`bash install.sh --claude-plugin` → `~/.claude/plugins/hyperlex`. Opening this
repo as a project uses `CLAUDE.md` plus `.claude/skills/` slash helpers.
Guide: [docs/claude-skill.md](./docs/claude-skill.md).

### Daily path (start here) — automatic backend

**One command = full results.** No manual chaining.

```bash
# AUTO: ingest → analyze → receipt → forecasts → score log → Phase 5 risk
$HLX pipeline "rizz" --route offline
# same:
$HLX run "rizz"
$HLX ingest "rizz"                 # full results (use --raw-only for signal only)

# Multi-term bag → one full result per atom automatically
$HLX pipeline "sigma rizz locked in"

# When network is allowed
$HLX pipeline "agentic slop" --route live
```

Settlement is the only manual step: `pending` → `settle` → `score-series`.

### Ingest routes

Prefer **routes** over raw adapter names:

| Route | Meaning | Network |
|-------|---------|---------|
| `offline` / `mock` / `default` | Deterministic fixture | no |
| `live` | Multi-source combine | yes |
| `glossary` | Betting glossary | yes |
| `social` | X / Twitter path | yes |

```bash
$HLX sources
$HLX sources --route live
```

Aliases: `real`→glossary · `x`→x_search · `firecrawl`→crawl4ai.  
`HYPERLEX_OFFLINE=1` forces mock for any network source.

### Calibration (where Brier is real)

```bash
$HLX pending
$HLX settle --forecast-id <id> --decision TRUE   # FALSE | VOID | CONFLICT
$HLX score-series --mean-shift --verify-chain
```

### Scan + advisory cron

```bash
$HLX scan \
  --config "$HERMES_SKILL_DIR/examples/cron/scan-queries.json" \
  --route offline --receipt --forecasts --append-log

$HLX risk-schedule --list-tiers
$HLX risk-schedule --tier MODERATE --schedule-out /tmp/hlx-cron
```

### Research (optional)

```bash
$HLX simulate --term rizz --mode scenario --domain ai
# Multi-term free text expands to separate atoms (sigma | rizz | locked in)
$HLX terms-split "sigma rizz locked in"
$HLX simulate --term "sigma rizz locked in" --domain ai
$HLX vector-seed --through 2026-08 --include-golden --include-home
$HLX vector-search "rizz" --kind term
$HLX archive-export --include-golden --history
```

### Backfill + populate the vector DB

```bash
export HYPERLEX_OFFLINE=1
$HLX lineage-backfill --list --through 2026-08

# Default SQLite
$HLX vector-seed --through 2026-08 --include-golden --include-home
$HLX vector-stats

# Local Chroma (iterate) → promote to Cloud when good
$HLX vector-seed --backend chroma --db ~/.hyperlex/chroma \
  --through 2026-08 --include-home --include-golden
$HLX vector-sync --from-path ~/.hyperlex/chroma --to cloud   # keys in ~/.hermes/.env
$HLX vector-stats --cloud

# One atom per run (do not blend independent terms into one seed)
$HLX run "rizz" --route offline
$HLX run "locked in" --route offline
$HLX run "sharp money" --route offline
```

Docs: [docs/modules/vectordb.md](./docs/modules/vectordb.md)

### Local data

```text
~/.hyperlex/receipts/
~/.hyperlex/receipt_ledger.jsonl
~/.hyperlex/score_log.jsonl
~/.hyperlex/cache/
~/.hyperlex/vector.db              # SQLite vectors
~/.hyperlex/chroma/                # local Chroma
```

**Week-one:** install → offline `run` → `pending` / `settle` / `score-series` → only then live routes or higher risk tiers.

Deep dive: [docs/operator-loop.md](./docs/operator-loop.md) · [docs/commands.md](./docs/commands.md)

---

## CLI surface

**Prefer**

| Command | Purpose |
|---------|---------|
| `commands` | Simplified map |
| `run "<q>" --route offline` | Daily one-shot |
| `pending` · `settle` · `score-series` | Calibration |
| `scan` · `risk-schedule` | Monitoring / cron envelopes |
| `sources` · `ingest` · `analyze` | Routing & partial pipeline |

**Also:** `doctor` · `relay` · `signal` · `diagram` · `simulate` · `vector-*` · `lineage-*` · `archive-*` · `ledger-*` · `smoke`

Package subset: `python -m hyperlex …`

---

## Library

```python
from hyperlex import (
    detect_memetic_patterns,
    pick_source,
    emit_receipt,
    extract_forecasts,
    settle_and_log,
    recompute_series,
    run_phase5_scenario,
    NOT_COMPUTABLE,
    PKG_VERSION,
)

src, _ = pick_source(route="offline")
result = detect_memetic_patterns(
    query="rizz",
    ingest_source=src,
    ingest_route="offline",
)
assert result["provenance"]["brier"] is None
```

API freeze: [docs/api-v1.md](./docs/api-v1.md) · `hyperlex.API_V1`

Optional Abraxas-shaped exports (no Abraxas import):

```python
from hyperlex.compat.abraxas import to_brier_ledger_entry, list_hlx_runes
```

---

## Status

| Area | Status |
|------|--------|
| Hermes skill + CI | Ready |
| Route-based ingest + `run` / `pending` | Ready |
| Lineage + YTD backfill / backprop | Ready |
| Receipts · settle · score-series | Ready |
| Risk → scan schedule (advisory) | Ready |
| Phase 5 research sim | Ready |
| Local vector DB | Ready |
| Pages run history | Ready |
| ANN backend | Deferred |
| Public PyPI | Not planned |

[ROADMAP.md](./ROADMAP.md) · [STATUS.md](./STATUS.md) · [CHANGELOG.md](./CHANGELOG.md)

---

## Docs & examples

| Resource | Purpose |
|----------|---------|
| [docs site](https://scrimshawlife-ctrl.github.io/Hyperlex/) | Workbench + run history |
| [docs/operator-loop.md](./docs/operator-loop.md) | Recommended burn-in |
| [docs/commands.md](./docs/commands.md) | Command map |
| [docs/modules/ingest.md](./docs/modules/ingest.md) | Routes & provenance |
| [docs/brier-calibration.md](./docs/brier-calibration.md) | Forecast → settle → Brier |
| [docs/phase5.md](./docs/phase5.md) | Research simulation |
| [docs/slang-lineages.md](./docs/slang-lineages.md) | Lineage methodology |
| [docs/hermes-skill.md](./docs/hermes-skill.md) | Hermes skill model |
| [docs/claude-skill.md](./docs/claude-skill.md) | Claude Code skill + plugin |

Examples: `examples/cron/` · `examples/receipts/golden/` · `examples/calibration/` · `examples/slang-families/` · `examples/case-studies/`

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md). Keep the settlement rule and offline-first defaults intact. Prefer small, test-backed PRs.

```bash
PYTHONPATH=src pytest -q
bash install.sh --dry-run
```

---

## License

MIT — [LICENSE](./LICENSE).

Built for operators who want memetic signal **with a receipt trail**, not a mood board.
