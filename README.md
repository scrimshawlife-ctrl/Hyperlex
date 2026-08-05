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
| **Version** | **0.3.2** |
| **Posture** | Hermes skill · Python package repo (≥3.10) · MIT |
| **Phases** | **0–4 complete** · **5.0** research simulation live |
| **Pages** | Static history of runs (not live operator DB) |
| **PyPI** | Not planned (local / Hermes install only) |

**Docs site:** https://scrimshawlife-ctrl.github.io/Hyperlex/  
**Status snapshot:** [STATUS.md](./STATUS.md)

---

## What Hyperlex is for

Hyperlex answers: *what is emerging in language/culture, which family does it belong to, how viral/hyperstitious is it, and can we score forecasts only after real outcomes?*

```text
ingest → analysis (lineage · typology · virality · hyperstition)
      → receipt (+ hash-chained ledger)
      → forecasts (probabilities only)
      → operator settle → Brier series
      → optional: relay / market signal / diagram / Phase 5 simulate
      → optional: archive-export --history → GitHub Pages
```

### Core functions

| Function | Role |
|----------|------|
| **Ingest** | `mock` offline, or glossary / reddit / urban / wiki / X / crawl |
| **Analyze** | Neologisms, lineage families (8 + 2026 YTD leaves), memetic typology, virality prediction (**SPECULATIVE**), hyperstition stage |
| **Receipts** | Integrity-hashed JSON + append-only local ledger |
| **Calibration** | Forecast extract → operator settle → Brier / BSS / Murphy / Yates (never invent scores) |
| **Relay** | `RUNE.HLX.*` envelopes + market-signal / hyperstition-feedback connectors |
| **Lineage ops** | YTD backfill packs + non-mutating lineage backpropagation |
| **Phase 5** | Cultural transmission, multi-agent memetics, hyperstition risk tiers, phylogeny scaffold |
| **Pages archive** | Publish-safe dated run history under `docs/archive/runs/` |

### Hard rules

1. **Brier requires settlement** — open analysis always has `provenance.brier = null`.
2. **Phase 5 is SPECULATIVE** — simulation packets also keep `brier: null`.
3. **No Abraxas hard import** — `hyperlex.compat.abraxas` is pure Hyperlex wire shapes for hosts.
4. **Primary store is local** — `~/.hyperlex/` (receipts, ledger, score log, cache). Pages is sanitized history only.

---

## Current status (ready surface)

| Area | Status |
|------|--------|
| Hermes skill install + `doctor` | Ready |
| Offline mock analyze | Ready |
| Lineage (8 families + 2026 YTD leaves) | Ready |
| YTD backfill + lineage backprop | Ready |
| Receipts / ledger / ledger-stats | Ready |
| Forecasts → settle → score-series | Ready |
| Rune relay + market connectors | Ready |
| Diagrams from history | Ready |
| Phase 5 simulate | Ready |
| Pages static run history | Ready |
| Governed LLM | Opt-in |
| Public PyPI | Not planned |

Roadmap: [ROADMAP.md](./ROADMAP.md) · Phase 5.1+ = domain phylogenies, sim calibration vs settled series, research exports.

---

## Install

```bash
bash install.sh --dry-run && bash install.sh
export HERMES_SKILL_DIR="${HOME}/.hermes/skills/hyperlex"
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" check
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" doctor
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" smoke
```

Editable package (optional):

```bash
pip install -e ".[dev]"
python -m hyperlex check
```

---

## Operator loop

```bash
export HERMES_SKILL_DIR="${HOME}/.hermes/skills/hyperlex"
H="$HERMES_SKILL_DIR/scripts/hyperlex.py"

# Analyze + receipt + forecasts
python3 "$H" analyze --query "sharp steam revenge" --source mock \
  --forecasts --receipt --out /tmp/hlx.json

# Relay / market packet
python3 "$H" relay --input /tmp/hlx.json --forecasts
python3 "$H" signal --input /tmp/hlx.json

# Phase 5 research scenario (SPECULATIVE)
python3 "$H" simulate --from-analyze --term "sigma rizz locked in" --domain ai

# Operator settlement → series
python3 "$H" settle --forecast-id <id> --decision TRUE
python3 "$H" score-series --mean-shift --verify-chain

# Lineage YTD + non-mutating rematch
python3 "$H" lineage-backfill --list --through 2026-08
python3 "$H" lineage-backprop --from-golden

# Append sanitized run to Pages history
python3 "$H" archive-export --include-golden --history
```

### Local data dirs

```text
~/.hyperlex/receipts/
~/.hyperlex/receipt_ledger.jsonl
~/.hyperlex/score_log.jsonl
~/.hyperlex/cache/
```

Repo packs: `data/backfill/2026/` (curated YTD slang).

---

## CLI surface (skill)

```text
check · doctor · sources · ingest · analyze · scan
emit-receipt · list-receipts · ledger-stats · ledger-diff
extract-forecasts · settle · score-series · verify-score-log
relay · signal · feedback · diagram
lineage-backfill · lineage-backprop
simulate                  # Phase 5
archive-export · archive-catalog
validate · verify-receipt · smoke
```

Package entry: `python -m hyperlex …` (subset of the skill CLI).

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
    run_phase5_scenario,       # Phase 5
    export_run_history,        # Pages archive
    NOT_COMPUTABLE,
    PKG_VERSION,
)

result = detect_memetic_patterns(query="sharp steam revenge", ingest_source="mock")
# result["provenance"]["brier"] is always None until settlement
```

Frozen symbol list: [docs/api-v1.md](./docs/api-v1.md) · `hyperlex.API_V1`  
Extended (additive): calibration connectors, diagrams, backfill, simulation, archive.

Abraxas-shaped modules (optional host import):

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

## Docs & examples

| Resource | Purpose |
|----------|---------|
| [STATUS.md](./STATUS.md) | Readiness snapshot |
| [SKILL.md](./SKILL.md) | Hermes skill contract |
| [SPEC.md](./SPEC.md) | Runtime surface |
| [docs/hermes-skill.md](./docs/hermes-skill.md) | Skill model + Abraxas boundary |
| [docs/brier-calibration.md](./docs/brier-calibration.md) | Forecast → settle → Brier |
| [docs/phase5.md](./docs/phase5.md) | Research simulation |
| [docs/slang-lineages.md](./docs/slang-lineages.md) | Lineage methodology |
| [ROADMAP.md](./ROADMAP.md) | Phases 0–5 |
| [docs site](https://scrimshawlife-ctrl.github.io/Hyperlex/) | Workbench + **run history catalog** |

Examples:

- `examples/receipts/golden/` — golden receipt corpus  
- `examples/calibration/` — settled Brier series fixture  
- `examples/slang-families/` — Mermaid lineage diagrams  
- `examples/cron/` — `LIVE_EMERGENCE_SCAN` job  
- `examples/case-studies/` — end-to-end walkthrough  

---

## License

MIT — see [LICENSE](./LICENSE).
