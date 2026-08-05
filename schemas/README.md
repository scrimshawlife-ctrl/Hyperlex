# Hyperlex Schemas

This directory contains the canonical JSON Schema definitions for Hyperlex components.

## Schemas

- **ingest.v1.schema.json** — Structured output from the `gate_of_intake` (expanded ingest layer)
- **result.v1.schema.json** — Full memetic analysis result from `detect_memetic_patterns`
- **receipt.v1.schema.json** — Canonical receipt with integrity hash (produced by `emit_receipt`)

## Usage

These schemas are used for validation in the reference implementation:

```python
from hyperlex import schemas
ok, msg = schemas.validate_result(result)
```

## Alignment

These schemas are part of the symbolic architecture defined in:
- `examples/hyperlex-symbolic/`
- `references/numogram.md`
- `references/chaos-magic.md`

They follow the same style as other Abraxas-Orchestra specs.

Version: 1.6.0
