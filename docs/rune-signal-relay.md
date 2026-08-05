# Rune / Signal Relay

Hyperlex emits **rune envelopes** that downstream Hermes/Abraxas systems can
bind without importing Hyperlex internals (and without Hyperlex importing Abraxas).

## Catalog

| Rune ID | Role | Source |
|---------|------|--------|
| `RUNE.HLX.LIVE_EMERGENCE_SCAN` | scan | analysis result |
| `RUNE.HLX.COMMUNICATION_RELAY` | signal | virality + hyperstition → actionable |
| `RUNE.HLX.CALIBRATION_FORECAST` | forecast | `extract_forecasts` |
| `RUNE.HLX.CALIBRATION_SERIES` | calibration | `score_series` / recompute |

Schema: `schemas/rune_envelope.v1.schema.json`  
Module: `hyperlex.relay`

## CLI

```bash
python3 scripts/hyperlex.py relay --list-runes

python3 scripts/hyperlex.py analyze --query "sharp steam" --source mock --out /tmp/r.json
python3 scripts/hyperlex.py relay --input /tmp/r.json --forecasts --out /tmp/envelopes.json
```

## Python

```python
from hyperlex import detect_memetic_patterns, relay_from_result, relay_series, recompute_series

result = detect_memetic_patterns("sharp steam", ingest_source="mock")
envelopes = relay_from_result(result)
# later, after settlements:
# relay_series(recompute_series())
```

## Authority

- Open scan/signal envelopes are **advisory**
- Series envelopes are `operator` only when `status=SCORED`
- Brier claims are `NOT_COMPUTABLE` until settlement

## Binding notes (Abraxas / Orchestra)

- Match on `rune_id` + `schema: hyperlex.rune_envelope.v1`
- Use `envelope_id` as idempotency key
- Do not treat `COMMUNICATION_RELAY.actionable` as execution authority
