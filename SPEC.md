# Hyperlex Technical Specification v1.6

## Public API

### ingest_signal(query: str, source: str = "mock") -> str
### fetch_ingest(query: str, source: str = "mock", structured: bool = True) -> dict

`ingest_signal` returns raw text (backward compatible).

`fetch_ingest` returns structured data with extracted terms and metadata.

Supported sources (expanded v1.6):
- "mock"
- "real" / "glossary" / "web" (Action Network)
- "reddit"
- "urban" (Urban Dictionary)
- "wikipedia"
- "x_search", "firecrawl" (stubs)
- "combined" (multi-source)

### detect_memetic_patterns(query: str = ..., ingest_source: str = "mock") -> dict
Returns full analysis dict.

### mock_integrate_with_external_signal(result: dict) -> dict
Returns:
```json
{
  "signal_id": "...",
  "virality_boost": float,
  "hyperstition_risk": "ACTUALIZING | DORMANT | ...",
  "confidence": float,
  "actionable": "MONITOR | ESCALATE | IGNORE",
  ...
}
```

### emit_receipt(result: dict, out_dir: str | None = None) -> Path
Writes timestamped receipt with integrity hash.

## Schemas

See the canonical schemas in the `schemas/` directory at repo root:

- `schemas/ingest.v1.schema.json`
- `schemas/result.v1.schema.json`
- `schemas/receipt.v1.schema.json`

Full details in `schemas/README.md`.

## Output Schema (detect_memetic_patterns) (deprecated - use root schemas)

```json
{
  "observed": "string",
  "inferred": "string",
  "speculative": "string",
  "provenance": {
    "canonical_hash": "16-char hex",
    "timestamp": "ISO8601",
    "version": "1.5.0",
    "brier": 0.89,
    "hyperstition_risk": "ACTUALIZING",
    "memclaw": "...",
    "arxiv_concepts_applied": ["neologism_pipeline", ...],
    "ingest_source": "real"
  },
  "analysis": {
    "neologisms": [{ "term": "...", "confidence": 0.0 }],
    "semantic_variation": { "sense": "...", "driver": "...", "community": "..." },
    "virality": {
      "hybrid_score": 0.0,
      "velocity": 0.0,
      "acceleration": 0.0
    },
    "memetics": {
      "is_memetic": true,
      "typology": "...",
      "score": 0.0
    },
    "hyperstition": {
      "loop_stage": "ACTUALIZING",
      "mechanism": "..."
    }
  },
  "notes": "...",
  "recommendation": "...",
  "receipt": { "path": "...", "integrity": "..." }
}
```

## Receipt Requirements
- Written to `~/.hyperlex/receipts/` by default (or provided out_dir)
- Filename: `hyperlex_{timestamp}.json`
- Must contain full result + receipt block

## Versioning
- Semantic versioning on package
- Breaking changes require major version + SPEC update here

## Error Handling
- Real ingest failures → graceful fallback with provenance note
- All errors visible in returned dict (no silent failures for public API)