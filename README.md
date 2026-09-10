# hyperlex

Standalone, installable Python package for **HYPERLEX (Memetic Emergence)** — memetic pattern detection, hyperstition tracking, virality scoring, and symbolic forecasting.

## Features
- Wired real ingest (`source="real"`, `"reddit"`, etc.)
- ArXiv-distilled modules (neologism pipeline, semantic variation, hybrid virality, memetics protocol, hyperstition loops)
- Strict JSON output with OBSERVED / INFERRED / SPECULATIVE + provenance + Brier
- Generic external signal integration (feeds virality + hyperstition into any pipeline)
- Fully decoupled (no Hollersports/Abraxas hard dependencies)

## Installation

### Editable (recommended for development)
```bash
cd /path/to/hyperlex
pip install -e ".[dev]"
```

### Normal install
```bash
pip install hyperlex
```

## Quick Usage

```python
from hyperlex import detect_memetic_patterns, mock_integrate_with_external_signal

# Real data
result = detect_memetic_patterns(
    query="sharp money revenge narrative",
    ingest_source="real"
)
print(result["analysis"]["virality"])
print(result["analysis"]["hyperstition"])

# Feed into downstream signal
signal = mock_integrate_with_external_signal(result)
print(signal["actionable"], signal["confidence"])
```

### CLI
```bash
hyperlex
# or
python -m hyperlex
```

## Run Tests
```bash
pytest
```

## Core Functions
- `ingest_signal(query, source="mock"|"real"|"reddit"|"x_search"|"firecrawl")`
- `detect_memetic_patterns(...)`
- `mock_integrate_with_external_signal(result)`
- `compute_virality_score(text)`
- `simulate_hyperstition_loop(narrative)`

See `src/hyperlex/engine.py` for full details and the original arXiv references.

## Moltbook + Agent Memory Integration (2026-09)
Hyperlex now ingests from Moltbook (AI agent network) for memetic patterns around:
- Tiered memory architectures (scratchpad/episodic/rubric)
- Context loss & re-entry costs
- Provenance / auditable memory (ECHO-style)
- Slang as load-bearing compression

Use `ingest_source="moltbook"` or `"agent_discourse"`.

See symbolic/SKELETON.md for the updated memetic memory mapping.

## Agent Memetics Classification (Moltbook + Hyperlex)
New capabilities from Moltbook research assimilation:
- `classify_compression_type()`: load_bearing vs decorative jargon/slang
- `compute_context_friction()`: re-entry costs, sliding window loss
- `detect_memetic_memory_patterns()`: tiered memory, provenance, KDR/ECHO patterns
- Seed dataset in `data/agent_memetics/seed_examples.jsonl`
- Classification boosted with curated examples

Use with `ingest_source="moltbook"` for live agent discourse signals.

### New: memetic_efficiency_score (Moltbook assimilation)
`compute_memetic_efficiency_score(text, memory_patterns, virality)` 
Composite score for transmission stickiness: (virality * (1-friction) * compression_factor * provenance * tier_diversity)

Used in batch analysis of agent memory posts. Higher scores indicate stronger hyperstition candidates in agent discourse.

See `examples/agent_memory_memetics.py` and `out/batch_moltbook_memetics.json`.
