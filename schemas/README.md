# Hyperlex Schemas

Canonical schemas for the Hyperlex skill.

## Analysis / receipts

- `ingest.v1.schema.json` — structured ingest records
- `result.v1.schema.json` — full analysis output
- `receipt.v1.schema.json` — result plus integrity receipt
- `lineage.v1.schema.json` — optional lineage attachment (`analysis.lineage`)

## Calibration

- `forecast.v1.schema.json` — probabilistic forecast extracted from a result
- `settlement.v1.schema.json` — resolved outcome for a forecast
- `brier_series.v1.schema.json` — aggregate BS / BSS / Murphy / Yates over settled pairs

Open analysis results must not claim a numeric Brier. Use calibration artifacts after settlement. See `docs/brier-calibration.md`.

## Validation

```python
from hyperlex import schemas
ok, msg = schemas.validate_result(result)
ok, msg = schemas.validate_receipt(payload)
ok, msg = schemas.validate_ingest(payload)
```

## Version

Version: 0.1.0 (+ lineage + calibration draft)
