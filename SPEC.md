# Hyperlex Technical Specification v0.1.0+

## Runtime API

### Package

- `ingest_signal(query: str, source: str = "mock") -> str`
- `fetch_ingest(query: str, source: str = "mock", structured: bool = True, max_terms: int = 8) -> dict`
- `detect_memetic_patterns(query: str = ..., ingest_source: str = "mock", use_structured_ingest: bool = False, validate: bool = False) -> dict`
- `mock_integrate_with_external_signal(result: dict) -> dict`
- `emit_receipt(result: dict, out_dir: str | Path | None = None, validate: bool = False) -> Path`
- `extract_forecasts(result: dict, receipt_ref: dict | None = None) -> list[dict]`
- `settle(forecast: dict, outcome_value: float, settlement_decision: str, ...) -> dict`
- `score_pair(forecast: dict, settlement: dict) -> dict`
- `score_series(pairs: list[tuple[dict, dict]], reference: str = "climatology") -> dict`

Supported sources:
- `mock`, `real`, `glossary`, `web`, `reddit`, `urban`, `wikipedia`, `combined`, `x_search`, `firecrawl`, `crawl4ai`

### Command Surface

```bash
python3 scripts/hyperlex.py check
python3 scripts/hyperlex.py sources
python3 scripts/hyperlex.py ingest <query> [--source ...] [--structured]
python3 scripts/hyperlex.py analyze [--query ...] [--source ...] [--structured-ingest] [--validate] [--forecasts] [--append-log]
python3 scripts/hyperlex.py analyze --input <ingest.json>
python3 scripts/hyperlex.py extract-forecasts --input <result.json> [--append-log]
python3 scripts/hyperlex.py settle --forecast-id <id> --decision TRUE|FALSE|VOID|CONFLICT
python3 scripts/hyperlex.py score-series [--mean-shift] [--verify-chain]
python3 scripts/hyperlex.py verify-score-log
python3 scripts/hyperlex.py validate <artifact.json>
python3 scripts/hyperlex.py verify-receipt <receipt.json>
python3 scripts/hyperlex.py smoke
```

## Output (canonical fields)

Result objects follow `schemas/result.v1.schema.json` and must include:
- `observed`, `inferred`, `speculative`
- `provenance` with at least `canonical_hash`, `timestamp`, `version`, `hyperstition_risk`, `ingest_source`
- `analysis` object

**Brier on open results:** `provenance.brier` must be `null` (or omitted) with optional `brier_note: "brier_requires_settlement"`. Numeric Brier values are only valid on calibration series artifacts after settlement.

Receipts follow `schemas/receipt.v1.schema.json` and embed a `receipt` block containing `path` and `integrity`.

### Calibration artifacts

- Forecasts: `schemas/forecast.v1.schema.json`
- Settlements: `schemas/settlement.v1.schema.json`
- Series scores: `schemas/brier_series.v1.schema.json`

See `docs/brier-calibration.md` for lifecycle and formulas.

## Error handling

- Ingest failures must not crash the runtime.
- Failures are exposed as explicit textual fallback content and optional schema metadata.
- Calibration scoring returns `NOT_COMPUTABLE` when pairs are missing or unscoreable.
- `scripts/hyperlex.py validate` and `verify-receipt` return non-zero exit code on invalid artifacts.
