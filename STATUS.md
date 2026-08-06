# Hyperlex Skill Status

**Version:** 0.4.0  
**Posture:** Hermes skill (Python package repo)  
**Install:** `bash install.sh` → `~/.hermes/skills/hyperlex`  
**Track:** Phases 0–4 complete · Phase 5.0–5.3 · Pages static run history · Hallmark desk UI

## Health

```bash
python3 scripts/hyperlex.py doctor
python3 scripts/release_preflight.py
python3 scripts/hyperlex.py simulate --term rizz --mode scenario
```

## Surface (ready)

| Area | Status |
|------|--------|
| Skill contract + install | Ready |
| Mock offline analyze | Ready |
| Lineage (8 families + 2026 YTD leaves) | Ready |
| YTD backfill packs (`data/backfill/2026/`) | Ready |
| Lineage backpropagation (non-mutating) | Ready |
| Typology + community drivers | Ready |
| Virality prediction (SPECULATIVE) | Ready |
| Receipts + ledger + ledger-stats/diff | Ready |
| Forecasts → settle → Brier series | Ready (settlement required) |
| Rune relay + market connectors | Ready |
| Diagrams from history | Ready |
| Case study runner | Ready |
| MkDocs + Pages (enabled) | Ready |
| Pages static run history | Ready (`docs/archive/runs/` + catalog) |
| Long-term analysis archive | Ready (`latest/` + dated runs) |
| Governed LLM (echo / openai_compatible) | Opt-in |
| **Phase 5 cultural transmission** | Ready |
| **Phase 5 multi-agent memetics** | Ready |
| **Phase 5 hyperstition risk** | Ready |
| **Phase 5 phylogeny scaffold** | Ready |
| **Local vector DB** (`~/.hyperlex/vector.db`) | Ready |
| **Chroma vector backend** (local path or Cloud) | Ready (opt-in · `HYPERLEX_VECTOR_BACKEND=chroma`) |
| **Hybrid lineage re-rank** | Ready (lexical + vector boost) |
| **Domain phylogeny packs** | Ready (`data/phylogeny/`) |
| **Transmission calibrate** | Ready (advisory β/γ from settled pairs) |
| **Scenario library + export** | Ready (`compare` / `export`) |
| **Risk → scan/cron schedule** | Ready (`risk-schedule`; advisory only) |
| **Ingest routes + `run`/`commands`/`pending`** | Ready (v0.3.8+) |
| **Atomic multi-term seeds** | Ready (v0.4.0 · `terms-split` / multi Phase 5) |
| **Pages demos (atomic terms)** | Ready (`docs/demos/atomic-terms.md`) |
| **Automatic pipeline** | Ready (v0.4.0 · `pipeline` / `run` / `ingest` → full results) |
| Public PyPI | Not planned |
| Abraxas hard import | Never |

## Operator loop

```text
pipeline "rizz" | ingest "rizz" | run "rizz"   # AUTO full results
  → pending → settle → score-series            # only manual step (Brier)
  → scan / risk-schedule                       # cron advisory
  → archive-export / vector-*                  # optional
```

## Data dirs

```text
~/.hyperlex/receipts/
~/.hyperlex/receipt_ledger.jsonl
~/.hyperlex/score_log.jsonl
~/.hyperlex/cache/
~/.hyperlex/vector.db            # local SQLite vector store (default)
~/.hyperlex/chroma/              # optional local Chroma persist (HYPERLEX_CHROMA_PATH)
data/backfill/2026/          # curated YTD term packs (repo)
```

## Recommended next (ops, not greenfield)

See [docs/operator-loop.md](docs/operator-loop.md) · [docs/demos/atomic-terms.md](docs/demos/atomic-terms.md):

1. `bash examples/ops/burn-in.sh` (atomic offline runs)
2. `pending` → `settle` → `score-series`
3. Register MODERATE cron from `risk-schedule` when ready
4. Defer ANN until vector corpus is large

## Phase 5.3+ (deferred)

Optional ANN backend if corpus grows past linear scan.
