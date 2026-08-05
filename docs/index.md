# Hyperlex

**Hermes skill** for memetic emergence analysis — implemented as a Python package repository.

```bash
bash install.sh
export HERMES_SKILL_DIR="${HOME}/.hermes/skills/hyperlex"
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" check
python3 "$HERMES_SKILL_DIR/scripts/run_case_study.py" --out-dir out/case-study
```

## What you get

- Ingest (mock offline, live glossary/reddit/urban/wiki/X/crawl)
- Lineage matching, typology, virality prediction (SPECULATIVE)
- Receipts + hash-chained ledger
- Forecasts → operator settlement → Brier series (never invent scores)
- RUNE.HLX.* envelopes + market-signal packets
- Mermaid diagrams from receipt history

## Principles

!!! warning "Brier requires settlement"
    Open analysis always has `provenance.brier = null`. Numeric Brier only after operator settlement.

!!! note "No Abraxas import"
    Relevant Abraxas wire shapes live under `hyperlex.compat.abraxas`. Hosts import *from* Hyperlex.

## Docs map

| Start here | Link |
|------------|------|
| Skill model | [hermes-skill.md](hermes-skill.md) |
| Frozen API | [api-v1.md](api-v1.md) |
| Case study | [case-studies.md](case-studies.md) |
| Calibration | [brier-calibration.md](brier-calibration.md) |

## Build this site

```bash
pip install -e ".[docs]"
mkdocs serve   # http://127.0.0.1:8000
mkdocs build   # site/
```
