# Hyperlex Technical Specification v1.5

## Public API

### ingest_signal(query: str, source: str = "mock") -> str
Returns raw observed signal text.

Supported sources:
- "mock"
- "real" (Action Network glossary)
- "reddit"
- "x_search" (stub)
- "firecrawl" (stub)

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

## Output Schema (detect_memetic_patterns)

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