# Hyperlex

**Hermes skill** for memetic emergence analysis — implemented as a Python package repository.  
**v0.3.0** · Phases 0–4 complete · Phase 5.0 research simulation active.

```bash
bash install.sh
export HERMES_SKILL_DIR="${HOME}/.hermes/skills/hyperlex"
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" check
python3 "$HERMES_SKILL_DIR/scripts/run_case_study.py" --out-dir out/case-study
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" simulate --term rizz --mode scenario
```

## What you get

- Ingest (mock offline, live glossary/reddit/urban/wiki/X/crawl)
- Lineage matching, typology, virality prediction (SPECULATIVE)
- YTD slang backfill + non-mutating lineage backpropagation
- Receipts + hash-chained ledger
- Forecasts → operator settlement → Brier series (never invent scores)
- RUNE.HLX.* envelopes + market-signal packets
- Mermaid diagrams from receipt history
- **Phase 5:** cultural transmission, multi-agent memetics, hyperstition risk, phylogeny scaffold

## Principles

!!! warning "Brier requires settlement"
    Open analysis always has `provenance.brier = null`. Numeric Brier only after operator settlement.
    Phase 5 simulation also keeps `brier: null` (SPECULATIVE research tooling).

!!! note "No Abraxas import"
    Relevant Abraxas wire shapes live under `hyperlex.compat.abraxas`. Hosts import *from* Hyperlex.

## Docs map

| Start here | Link |
|------------|------|
| Skill model | [hermes-skill.md](hermes-skill.md) |
| Frozen API | [api-v1.md](api-v1.md) |
| Phase 5 simulation | [phase5.md](phase5.md) · [modules/simulation.md](modules/simulation.md) |
| Case study | [case-studies.md](case-studies.md) |
| Calibration | [brier-calibration.md](brier-calibration.md) |
| Slang lineages | [slang-lineages.md](slang-lineages.md) |
| Skill status | see repo `STATUS.md` |

## Build this site

```bash
pip install -e ".[docs]"
python3 scripts/sync_mkdocs_pages.py
mkdocs serve   # http://127.0.0.1:8000
mkdocs build --strict
```

GitHub Pages deploys from `.github/workflows/docs.yml` on `main`  
(enable **Settings → Pages → Source: GitHub Actions** once).

Public URL (after Pages is enabled):  
https://scrimshawlife-ctrl.github.io/Hyperlex-Hermes-Specs/

## Long-term analysis archive

Sanitized ingest summaries can live on Pages for historical review:

```bash
python3 scripts/hyperlex.py archive-export --include-golden --out-dir docs/archive/latest
```

See [archive/latest](archive/latest/index.md). Primary store remains `~/.hyperlex/`.

## Skill health

```bash
python3 scripts/hyperlex.py doctor
python3 scripts/hyperlex.py ledger-stats
python3 scripts/release_preflight.py
```
