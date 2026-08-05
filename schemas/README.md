# Hyperlex Schemas

Canonical schemas for the Hyperlex skill.

- `ingest.v1.schema.json` — structured ingest records
- `result.v1.schema.json` — full analysis output
- `receipt.v1.schema.json` — result plus integrity receipt
- `lineage.v1.schema.json` — optional lineage attachment for analysis results (family_id, matched_terms, confidence, diagram_ref, etc.)

## Validation

```python
from hyperlex import schemas
ok, msg = schemas.validate_result(result)
ok, msg = schemas.validate_receipt(payload)
ok, msg = schemas.validate_ingest(payload)
```

Lineage objects follow `lineage.v1.schema.json` and are attached under `analysis.lineage` when a match is found.

## Version

Version: 0.1.0 (+ lineage draft)
