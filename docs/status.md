# Hyperlex Skill Status

**Version:** 0.3.4  
**Posture:** Hermes skill (Python package repo)  
**Install:** `bash install.sh` → `~/.hermes/skills/hyperlex`  
**Track:** Phases 0–4 complete · Phase 5.0 · Pages static run history · Hallmark desk UI

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
| Public PyPI | Not planned |
| Abraxas hard import | Never |

## Operator loop

```text
analyze --receipt --forecasts --append-log
  → relay / signal / diagram
  → settle (operator)
  → score-series / feedback
  → lineage-backfill --list / lineage-backprop --from-golden
  → simulate --from-analyze --domain markets|ai|politics   # Phase 5
  → archive-export --history   # append sanitized run to Pages history
  → vector-seed / vector-search   # local vector DB
```

## Data dirs

```text
~/.hyperlex/receipts/
~/.hyperlex/receipt_ledger.jsonl
~/.hyperlex/score_log.jsonl
~/.hyperlex/cache/
~/.hyperlex/vector.db            # local SQLite vector store
data/backfill/2026/          # curated YTD term packs (repo)
```

## Phase 5.1+ (next)

Domain phylogeny libraries, sim parameter calibration against settled series,
comparative multi-agent runs over archive snapshots, research export templates.
