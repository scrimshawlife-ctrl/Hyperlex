---
name: hyperlex
description: >
  Use when the user wants memetic emergence analysis, slang detection,
  hyperstition / virality scoring, slang lineage matching, forecast extraction,
  operator settlement, or Brier calibration on cultural signals. Triggers
  include slang, memetics, hyperstition, virality, lineage, Brier, settle
  forecasts, score-series, betting slang, crypto-degen slang, ai-native slang,
  brainrot, and receipt-backed cultural signal scans. Not for general web
  research (use agent-reach), product audits (neon-genie), or cinematic work
  (kubrick).
version: 0.1.1
author: Applied Alchemy Labs / Hermes
license: MIT
platforms: [linux, macos]
dependencies: []
metadata:
  hermes:
    tags:
      - Memetics
      - Slang
      - Hyperstition
      - Virality
      - Lineage
      - Calibration
      - Brier
      - Receipts
      - Forecasting
    category: analysis
    related_skills: []
  openclaw:
    requires:
      bins: [python3]
    os: [darwin, linux]
    emoji: "🌀"
triggers:
  - hyperlex
  - memetic
  - memetics
  - slang
  - slang lineage
  - hyperstition
  - virality
  - neologism
  - betting slang
  - sharp money
  - brainrot
  - brier
  - settle forecast
  - score series
  - cultural signal
  - memetic receipt
---

# Hyperlex

Standalone **Hermes skill** for memetic emergence analysis.

Hermes loads this directory and uses `SKILL.md` as the behavior contract.
The runtime is the bundled Python package under `src/hyperlex/` plus the CLI
at `scripts/hyperlex.py`. No Abraxas import, no required network for baseline
(`mock`) mode.

Resolve paths from the installed skill root. Set:

```bash
export HERMES_SKILL_DIR="${HERMES_SKILL_DIR:-$HOME/.hermes/skills/hyperlex}"
```

## When to Use

- Detect slang / neologisms and score virality, memetics, hyperstition
- Match slang into historical **lineage families** with transparent confidence
- Emit integrity-hashed **receipts** for auditable runs
- Extract **forecasts** from analysis (probabilities only — no fake Brier)
- **Settle** forecasts as an operator and recompute Brier series from the score log
- Scan betting-sharp, crypto-degen, ai-native, brainrot, kinship, political-status families

## When Not to Use

- General multi-platform web research → agent-reach
- Product / opportunity intelligence → neon-genie
- Cinematic continuity / storyboards → kubrick
- Symbolic code architecture mapping → orchestra

## Prerequisites

- Python 3.10+
- `python3` on PATH
- Optional: `requests`, `jsonschema`, `crawl4ai` for richer ingest / validation
- Optional: network for non-`mock` sources

## Install

```bash
bash install.sh --dry-run
bash install.sh
# installs to ~/.hermes/skills/hyperlex by default
python3 "$HOME/.hermes/skills/hyperlex/scripts/hyperlex.py" check
python3 "$HOME/.hermes/skills/hyperlex/scripts/hyperlex.py" smoke
```

## Commands

All commands run from the skill root (or with absolute path to the CLI):

```bash
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" check
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" sources
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" ingest "<query>" --source mock
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" analyze --query "<query>" --source mock [--validate] [--forecasts]
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" extract-forecasts --input <result.json> [--append-log]
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" settle --forecast-id <id> --decision TRUE|FALSE|VOID|CONFLICT [--export-ledger]
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" score-series [--mean-shift] [--verify-chain]
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" verify-score-log
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" validate <artifact.json>
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" verify-receipt <receipt.json>
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" smoke
```

### Operator calibration path

```text
analyze --forecasts --append-log
  → settle --forecast-id … --decision TRUE|FALSE
  → score-series [--mean-shift] [--verify-chain]
```

- Score log default: `~/.hyperlex/score_log.jsonl`
- Override: `HYPERLEX_SCORE_LOG`, `--log`, or `--repo-log` → `out/calibration/score_log.jsonl`
- **Never** emit numeric Brier without settlement. Empty series → `NOT_COMPUTABLE`.

## Preferred sequence

1. **Classify** — ingest only vs full analysis vs settle/score.
2. **Ingest** — prefer `mock` for deterministic checks; real sources when network allowed.
3. **Analyze** — `detect_memetic_patterns` / `analyze`; attach lineage when confidence ≥ 0.42.
4. **Receipt** — serious runs call `emit_receipt` (or keep CLI analysis output + verify later).
5. **Forecast** — `extract_forecasts` or `analyze --forecasts`; probabilities only.
6. **Settle** — operator authority required; `TRUE`/`FALSE` score; `VOID`/`CONFLICT` do not score.
7. **Series** — `score-series` recomputes BS, BSS, Murphy, Ferro–Fricker, Yates, Vieira, Δf.
8. **Label claims** — `OBSERVED` / `INFERRED` / `SPECULATIVE`; fail closed on missing outcomes.

## Public API (package)

```python
from hyperlex import (
    ingest_signal, fetch_ingest, detect_memetic_patterns,
    match_lineage, emit_receipt, extract_forecasts,
    settle_and_log, recompute_series, score_pair, score_series,
    NOT_COMPUTABLE,
)

result = detect_memetic_patterns(query="sharp steam revenge", ingest_source="mock")
forecasts = extract_forecasts(result)
# later, after operator review:
# settle_and_log(forecast, outcome_value=1.0, settlement_decision="TRUE")
# recompute_series()
```

Ensure `src/` is on `PYTHONPATH` when importing outside the CLI
(CLI inserts `src/` automatically).

## Authority boundaries

Hyperlex **may**:

- ingest and analyze signals
- match lineages with transparent score breakdowns
- extract forecasts and write receipts / score-log events
- compute Brier only from settled pairs
- export Abraxas-compatible ledger shapes (no Abraxas import)

Hyperlex **may not**:

- invent numeric Brier on open analysis (`provenance.brier` stays `null`)
- auto-settle without authority marker
- promote speculative hyperstition stages as hard truth
- mutate Abraxas or other systems (export is optional and offline)

## Pitfalls

- `scripts/hyperlex.py` must not shadow the package: always run via the skill path so `src/` is first on `sys.path`.
- Non-`mock` sources need network and may degrade gracefully — check ingest metadata.
- Lineage confidence is **INFERRED**; do not treat it as observed ground truth.
- Mean-shift from `score-series --mean-shift` is **advisory** for future forecasts only.
- Score log is append-only; series is recomputed from the log, not stored as sole truth.

## Verification

```bash
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" check
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" smoke
```

Successful packaging:

- `~/.hermes/skills/hyperlex/SKILL.md` exists
- `check` returns `"ok": true`
- `smoke` writes a receipt under `out/smoke/`
- Open analysis has `"brier": null`

## Design references

- `DESIGN.md` — principles (incl. 11 lineage, 12 Brier requires settlement)
- `docs/brier-calibration.md` — forecast → settlement → score
- `docs/slang-lineages.md` — family methodology
- `schemas/` — ingest, result, receipt, forecast, settlement, brier_series, lineage
- `examples/slang-families/` — Mermaid + HTML family diagrams
- `references/hermes-runtime-contract.md` — path / authority policy

## Security

Local stdlib-first CLI. Baseline (`mock`) needs no network. Real ingest may call public web APIs. Score log and receipts are local files under `~/.hyperlex/` or skill `out/`.
