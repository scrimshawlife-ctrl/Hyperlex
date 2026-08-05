# Hyperlex Architecture

## High-Level Overview
Hyperlex is a **pure function + side-effect minimal** engine.

```
Input (query + ingest_source)
    ↓
    Ingest Layer (real / mock / reddit / x / firecrawl / crawl4ai)
    ↓
Analysis Core (arXiv-grounded modules)
    ↓
Integration Layer (external signal)
    ↓
Receipt Emitter (provenance + integrity)
    ↓
Output (strict JSON) + optional side effects
```

## Core Modules

### 1. Ingest Layer (`ingest_signal`)
- `source="real"`: Action Network glossary scraper (live)
- `source="reddit"`: Best-effort Reddit search
- `source="mock"`: Deterministic fallback
- `x_search`: placeholder
- `firecrawl` and `crawl4ai`: Crawl4AI-backed web crawl adapters

### 2. Analysis Core
- `detect_memetic_patterns`
  - `detect_neologisms`
  - `trace_semantic_variation`
  - `compute_virality_score` (hybrid)
  - `memetics_protocol_check`
  - `simulate_hyperstition_loop`

### 3. Integration Layer
- `mock_integrate_with_external_signal`
  - Extracts virality_boost, hyperstition_risk, confidence, actionable
  - Designed to feed any downstream (market signals, forecasts, runes)

### 4. Provenance & Receipts
- Every run produces canonical hash
- `emit_receipt()` writes timestamped, integrity-hashed JSON
- Brier baseline carried in provenance

## Data Flow (Strict)
All public functions return or accept only:
- Plain Python dicts / strings
- No hidden state
- Deterministic when possible

## Package Structure (Implementation)
```
hyperlex/
├── __init__.py          # Public API
├── engine.py            # Core logic + arXiv modules
├── __main__.py          # CLI
tests/
out/                     # Local artifacts
```

## Integration Points (Future)
- Hermes skills / cron
- Hollersports-style calibration (decoupled)
- Generic market / narrative signal pipelines
- Abraxas symbolic intelligence

## Constraints
- No synthetic data
- Real ingest preferred
- Append-only ledgers for serious use
- Governed LLM use only (when added)
- Python 3.10+

See SPEC.md for exact interfaces and schemas.
