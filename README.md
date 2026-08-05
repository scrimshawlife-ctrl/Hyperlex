<p align="center">
  <img src="assets/hyperlex-hero.jpg" alt="Hyperlex — Memetic Emergence Engine" width="720">
</p>

# Hyperlex

**Standalone memetic emergence engine** — slang, lineage, hyperstition, virality,
receipts, settled Brier calibration, and HLX rune relay.

Version **0.2.2** · Skill: `hyperlex` · Python ≥ 3.10 · License: MIT  
**Not** an Abraxas dependency. Relevant Abraxas wire shapes ship as Hyperlex modules.

## What it does

1. Ingest cultural signals (`mock` offline, or live glossary/reddit/urban/wiki/X/crawl)
2. Analyze neologisms, lineage families, virality, memetics, hyperstition
3. Emit integrity-hashed **receipts** + optional receipt ledger
4. Extract **forecasts** (probabilities only — never fake Brier)
5. **Settle** outcomes → score log → Murphy/Yates/Vieira series diagnostics
6. Emit **RUNE.HLX.*** envelopes and generic market/forecast connector packets

## Install (Hermes skill)

```bash
bash install.sh --dry-run && bash install.sh
export HERMES_SKILL_DIR="${HOME}/.hermes/skills/hyperlex"
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" check
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" smoke
```

Local package (optional):

```bash
pip install -e ".[dev]"
python -m hyperlex check
```

## Quick start

```bash
export HERMES_SKILL_DIR="${HOME}/.hermes/skills/hyperlex"
H="$HERMES_SKILL_DIR/scripts/hyperlex.py"

python3 "$H" analyze --query "sharp steam revenge" --source mock \
  --forecasts --receipt --out /tmp/hlx.json

python3 "$H" relay --input /tmp/hlx.json --forecasts
python3 "$H" signal --input /tmp/hlx.json

# later — operator settlement
python3 "$H" settle --forecast-id <id> --decision TRUE
python3 "$H" score-series --mean-shift --verify-chain
python3 "$H" feedback --signal-key hyperstition.stage
```

## Design surface

| Doc | Purpose |
|-----|---------|
| [SKILL.md](./SKILL.md) | Hermes contract |
| [SPEC.md](./SPEC.md) | Runtime API |
| [docs/api-v1.md](./docs/api-v1.md) | **Frozen public API** |
| [docs/standalone-app.md](./docs/standalone-app.md) | Standalone + Abraxas modules |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System layout |
| [DESIGN.md](./DESIGN.md) | Principles |
| [ROADMAP.md](./ROADMAP.md) | Canonical roadmap |
| [docs/brier-calibration.md](./docs/brier-calibration.md) | Forecast → settle → Brier |
| [docs/rune-signal-relay.md](./docs/rune-signal-relay.md) | RUNE.HLX.* |
| [QUICKSTART.md](./QUICKSTART.md) | Operator path |

## Abraxas-compatible modules (import from Hyperlex)

```python
from hyperlex.compat.abraxas import (
    to_brier_ledger_entry,
    to_brier_score_packet,
    to_operator_brier_review,
    list_hlx_runes,
    envelopes_from_result,
)
```

## Examples

- `examples/receipts/golden/` — golden receipt corpus
- `examples/calibration/settled_series.v1.json` — golden Brier pairs
- `examples/slang-families/` — lineage Mermaid diagrams
- `examples/cron/` — LIVE_EMERGENCE_SCAN Hermes job

## License

MIT (see [LICENSE](./LICENSE)).
