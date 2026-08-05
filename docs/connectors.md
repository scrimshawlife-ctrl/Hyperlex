# Connectors — market signal & hyperstition feedback

Standalone outbound packets. No host imports required.

## Market signal

```bash
python3 scripts/hyperlex.py signal --input result.json
```

```python
from hyperlex import detect_memetic_patterns, build_market_signal, build_forecast_pipeline

result = detect_memetic_patterns("sharp steam", ingest_source="mock")
sig = build_market_signal(result)           # hyperlex.market_signal.v1
pipe = build_forecast_pipeline(result)      # hyperlex.forecast_pipeline.v1
```

| Field | Meaning |
|-------|---------|
| `actionable` | `IGNORE` / `MONITOR` / `ESCALATE` — **advisory only** |
| `brier` | always `null` until settlement |
| `authority` | `advisory` |

## Hyperstition feedback

Closed loop for **future** `hyperstition.stage` maps from settled series:

```bash
python3 scripts/hyperlex.py feedback --signal-key hyperstition.stage
```

```python
from hyperlex import recompute_series, hyperstition_feedback_from_series, extract_forecasts

series = recompute_series(signal_key="hyperstition.stage")
fb = hyperstition_feedback_from_series(series)
if fb["status"] == "ADVISORY":
    forecasts = extract_forecasts(result, hyperstition_stage_map=fb["advised_map"])
```

Rules:
- Never rewrites historical forecasts
- Max stage-map step capped (default 0.08)
- Adopt only when operator accepts; prefer bumping `mapping_version`
