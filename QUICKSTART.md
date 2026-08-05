# Hyperlex Quickstart

Hermes skill backed by this Python package repo.

## Install

```bash
bash install.sh
export HERMES_SKILL_DIR="${HOME}/.hermes/skills/hyperlex"
H="$HERMES_SKILL_DIR/scripts/hyperlex.py"
python3 "$H" check && python3 "$H" smoke
```

## Full operator loop

```bash
# 1. Analyze + receipt + forecasts
python3 "$H" analyze --query "sharp steam revenge" --source mock \
  --forecasts --receipt --append-log --out /tmp/hlx.json

# 2. Rune envelopes + market/forecast packets
python3 "$H" relay --input /tmp/hlx.json --forecasts
python3 "$H" signal --input /tmp/hlx.json

# 3. Settle (operator)
python3 "$H" settle --forecast-id <id> --decision TRUE \
  --authority-note "review confirmed"

# 4. Score series + optional hyperstition feedback
python3 "$H" score-series --mean-shift --verify-chain
python3 "$H" feedback --signal-key hyperstition.stage

# 5. Cron scan
python3 "$H" scan --config "$HERMES_SKILL_DIR/examples/cron/scan-queries.json" \
  --source mock --receipt --forecasts --append-log
```

## Library

```python
from hyperlex import (
    detect_memetic_patterns, extract_forecasts, emit_receipt,
    settle_and_log, recompute_series, build_market_signal,
    hyperstition_feedback_from_series,
)
from hyperlex.compat.abraxas import to_brier_ledger_entry, list_hlx_runes

result = detect_memetic_patterns("sharp steam", ingest_source="mock")
assert result["provenance"]["brier"] is None
emit_receipt(result)
sig = build_market_signal(result)
```

## Docs

- [docs/api-v1.md](docs/api-v1.md) — frozen API
- [docs/hermes-skill.md](docs/hermes-skill.md) — architecture posture
- [docs/connectors.md](docs/connectors.md) — signal + feedback
- [docs/brier-calibration.md](docs/brier-calibration.md)
