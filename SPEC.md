# Hyperlex Technical Specification v0.1.0

## Runtime API

### Package

- `ingest_signal(query: str, source: str = "mock") -> str`
- `fetch_ingest(query: str, source: str = "mock", structured: bool = True, max_terms: int = 8) -> dict`
- `detect_memetic_patterns(query: str = ..., ingest_source: str = "mock", use_structured_ingest: bool = False, validate: bool = False) -> dict`
- `mock_integrate_with_external_signal(result: dict) -> dict`
- `emit_receipt(result: dict, out_dir: str | Path | None = None, validate: bool = False) -> Path`

Supported sources:
- `mock`, `real`, `glossary`, `web`, `reddit`, `urban`, `wikipedia`, `combined`, `x_search`, `firecrawl`, `crawl4ai`

### Command Surface

Executable entrypoint:

```bash
python3 scripts/hyperlex.py check
python3 scripts/hyperlex.py sources
python3 scripts/hyperlex.py ingest <query> [--source ...] [--structured]
python3 scripts/hyperlex.py analyze [--query ...] [--source ...] [--structured-ingest] [--validate]
python3 scripts/hyperlex.py analyze --input <ingest.json>
python3 scripts/hyperlex.py validate <artifact.json>
python3 scripts/hyperlex.py verify-receipt <receipt.json>
```

## Output (canonical fields)

Result objects follow `schemas/result.v1.schema.json` and must include:
- `observed`, `inferred`, `speculative`
- `provenance` with at least `canonical_hash`, `timestamp`, `version`, `brier`, `hyperstition_risk`, `ingest_source`
- `analysis` object

Receipts follow `schemas/receipt.v1.schema.json` and embed a `receipt` block
containing `path` and `integrity`.

## Error handling

- Ingest failures must not crash the runtime.
- Failures are exposed as explicit textual fallback content and optional schema metadata.
- `scripts/hyperlex.py validate` and `verify-receipt` return non-zero exit code on invalid artifacts.
