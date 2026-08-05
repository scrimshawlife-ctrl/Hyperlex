# Hyperlex Skill Status

**Version:** 0.2.10  
**Posture:** Hermes skill (Python package repo)  
**Install:** `bash install.sh` → `~/.hermes/skills/hyperlex`

## Health

```bash
python3 scripts/hyperlex.py doctor
python3 scripts/release_preflight.py
```

## Surface (ready)

| Area | Status |
|------|--------|
| Skill contract + install | Ready |
| Mock offline analyze | Ready |
| Lineage (8 families) | Ready |
| Typology + community drivers | Ready |
| Virality prediction (SPECULATIVE) | Ready |
| Receipts + ledger + ledger-stats/diff | Ready |
| Forecasts → settle → Brier series | Ready (settlement required) |
| Rune relay + market connectors | Ready |
| Diagrams from history | Ready |
| Case study runner | Ready |
| MkDocs + Pages workflow | Ready |
| Governed LLM (echo / openai_compatible) | Opt-in |
| Public PyPI | Not planned |
| Abraxas hard import | Never |

## Operator loop

```text
analyze --receipt --forecasts --append-log
  → relay / signal / diagram
  → settle (operator)
  → score-series / feedback
  → ledger-stats
```

## Data dirs

```text
~/.hyperlex/receipts/
~/.hyperlex/receipt_ledger.jsonl
~/.hyperlex/score_log.jsonl
~/.hyperlex/cache/
```

## Not in scope (Phase 5+)

Multi-agent simulation, cultural transmission engines, full phylogenies.
