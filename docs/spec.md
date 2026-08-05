# Hyperlex Technical Specification v0.2

**Hermes skill (Python package repo).** No hard dependency on Abraxas. Relevant Abraxas wire
capabilities are Hyperlex modules under `hyperlex.compat.abraxas`.

API freeze: [`docs/api-v1.md`](docs/api-v1.md) · `hyperlex.API_V1`

## Runtime API (frozen symbols)

### Ingest & analysis
- `ingest_signal(query: str, source: str = "mock") -> str`
- `fetch_ingest(query, source="mock", structured=True, max_terms=8) -> dict`
- `detect_memetic_patterns(query=..., ingest_source="mock", use_structured_ingest=False, validate=False) -> dict`
- `match_lineage(text, terms=None, min_confidence=0.42) -> dict | None`
- `compute_lineage_confidence(hits, family_terms, corpus) -> (float, dict)`

### Receipts
- `emit_receipt(result, out_dir=None, validate=False, append_ledger=True, ledger_path=None) -> Path`
- `verify_receipt(payload) -> (bool, str)`

### Calibration
- `extract_forecasts(result, receipt_ref=None) -> list[dict]`
- `settle(forecast, outcome_value, settlement_decision, ...) -> dict`
- `score_pair(forecast, settlement) -> dict`
- `score_series(pairs, reference="climatology") -> dict`
- `settle_and_log(...)` / `recompute_series(path=None, ...)`
- `NOT_COMPUTABLE`

### Relay
- `relay_from_result(result) -> list[envelope]`
- `relay_forecasts(forecasts) -> envelope`
- `relay_series(series) -> envelope`
- `list_runes() -> list[dict]`

### Synthesis
- `mock_integrate_with_external_signal(result) -> dict`

### Compat (optional host import)
```python
from hyperlex.compat.abraxas import (
    to_brier_ledger_entry,
    to_brier_score_packet,
    to_operator_brier_review,
    list_hlx_runes,
    envelopes_from_result,
    CLAIM_LABELS,
)
```

## Sources

`mock`, `real`, `glossary`, `glossary_expanded`, `web`, `reddit`, `urban`,
`wikipedia`, `x_search`, `firecrawl`, `crawl4ai`, `combined`

## Command surface

### Hermes skill CLI (`scripts/hyperlex.py`)
```bash
check | sources | ingest | analyze | scan | relay
extract-forecasts | settle | score-series | verify-score-log
emit-receipt | list-receipts | verify-receipt-ledger | validate | verify-receipt | smoke
```

### Package CLI
```bash
python -m hyperlex check|analyze|scan|relay|settle|score-series|version
```

## Output contracts

### Analysis result
- `observed`, `inferred`, `speculative`
- `provenance`: `canonical_hash`, `timestamp`, `version`, `ingest_source`,
  `hyperstition_risk`, `brier: null`, `source_fingerprint`, …
- `analysis`: neologisms, virality, memetics, hyperstition, optional lineage

### Calibration
- Forecasts: `schemas/forecast.v1.schema.json` — never attach Brier
- Settlements: `schemas/settlement.v1.schema.json`
- Series: `schemas/brier_series.v1.schema.json` — empty → `NOT_COMPUTABLE`
- Rune envelopes: `schemas/rune_envelope.v1.schema.json`

## Error handling

- Ingest failures degrade; do not crash
- Missing settlements → `NOT_COMPUTABLE`
- CLI validate / verify-receipt exit non-zero on failure
