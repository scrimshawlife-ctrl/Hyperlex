# Hyperlex Skill Status

**Version:** 0.4.0  
**Posture:** Hermes skill (Python package repo)  
**Install:** `bash install.sh` → `~/.hermes/skills/hyperlex`  
**Claude (optional):** `bash install.sh --claude` → `~/.claude/skills/hyperlex`  
**Track:** Phases 0–4 complete · Phase 5.0–5.3 · Pages static run history · Hallmark desk UI

## Health

```bash
python3 scripts/hyperlex.py doctor
python3 scripts/release_preflight.py
python3 scripts/hyperlex.py simulate --term rizz --mode scenario
python -m hyperlex inbox list
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
| Pages static run history | Ready |
| Long-term analysis archive | Ready |
| Governed LLM (echo / openai_compatible) | Opt-in |
| Phase 5 cultural transmission / multi-agent / risk / phylogeny | Ready |
| Local vector DB + Chroma promote | Ready |
| Mutation prediction | Ready (SPECULATIVE) |
| Hybrid lineage re-rank | Ready |
| Domain phylogeny packs | Ready |
| Transmission calibrate / scenario library | Ready |
| Risk → scan/cron schedule | Ready (advisory) |
| Ingest routes + automatic pipeline | Ready |
| Atomic multi-term seeds | Ready |
| **Analysis enrichment** (compression_metrics, typology tags, signal_report, integrity header) | Ready |
| **Local attractor store** (`~/.hyperlex/signals/`) | Ready (`inbox list\|push\|clear`) |
| **Attractor candidate rune** (`RUNE.HLX.ATTRACTOR_CANDIDATE`) | Ready (advisory only) |
| Public PyPI | Not planned |
| External system hard import | Never |

## Operator loop

```text
pipeline "rizz" | run "rizz"
  → pending → settle → score-series
  → scan / risk-schedule
  → relay --push-inbox          # attractor envelope + local store
  → inbox list
  → vector-seed / vector-sync
  → archive-export
```

## Data dirs

```text
~/.hyperlex/receipts/
~/.hyperlex/receipt_ledger.jsonl
~/.hyperlex/score_log.jsonl
~/.hyperlex/mutation_watch.jsonl   # mutation grammar instrumentation (not Brier)
~/.hyperlex/cache/
~/.hyperlex/vector.db
~/.hyperlex/chroma/
~/.hyperlex/signals/inbox.jsonl   # high-priority attractor candidates
data/backfill/2026/
```

## Recommended next

1. Burn-in offline runs + settle path
2. Optional: enrich `scan` with focus / time_window / min_virality
3. Optional: daily aggregate forage receipt
