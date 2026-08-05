# Hyperlex Quickstart

Hermes skill backed by this Python package repo. Full guide: [README.md](./README.md) · [docs/operator-loop.md](./docs/operator-loop.md).

## Install

```bash
bash install.sh
export HERMES_SKILL_DIR="${HOME}/.hermes/skills/hyperlex"
export HLX="python3 $HERMES_SKILL_DIR/scripts/hyperlex.py"
$HLX check && $HLX smoke && $HLX commands
```

## Daily path

```bash
# One-shot: analyze + receipt + forecasts + score log (offline-safe)
$HLX run "sharp steam revenge" --route offline

# Open forecasts → settle → Brier series
$HLX pending
$HLX settle --forecast-id <id> --decision TRUE
$HLX score-series --mean-shift --verify-chain
```

## Ingest routes

```bash
$HLX sources
$HLX run "…" --route offline   # mock
$HLX run "…" --route live      # combined (needs network)
$HLX run "…" --route glossary
$HLX run "…" --route social
```

## Scan + advisory cron

```bash
$HLX scan --config "$HERMES_SKILL_DIR/examples/cron/scan-queries.json" \
  --route offline --receipt --forecasts --append-log

$HLX risk-schedule --tier MODERATE --schedule-out /tmp/hlx-cron
```

## Library

```python
from hyperlex import (
    detect_memetic_patterns, extract_forecasts, emit_receipt,
    settle_and_log, recompute_series, pick_source,
)
from hyperlex.compat.abraxas import to_brier_ledger_entry, list_hlx_runes

src, _ = pick_source(route="offline")
result = detect_memetic_patterns("sharp steam", ingest_source=src, ingest_route="offline")
assert result["provenance"]["brier"] is None
emit_receipt(result)
```

## Docs

- [docs/commands.md](docs/commands.md) — command map  
- [docs/modules/ingest.md](docs/modules/ingest.md) — routes  
- [docs/brier-calibration.md](docs/brier-calibration.md)  
- [docs/hermes-skill.md](docs/hermes-skill.md)  
