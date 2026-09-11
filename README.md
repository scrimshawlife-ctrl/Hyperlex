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

## Latest Continuation
- 18 Moltbook seeds (added "rented cognition/memory" example)
- Tier detection now reliably surfaces 'episodic' for KDR, rented, simplexity, SIGBUS, etc.
- memetic_efficiency exposed at top level of detect result
- Fresh batch analysis in out/batch_moltbook_memetics.json (18 seeds)
- Heartbeat logs efficiency/tiers
- All 20 tests pass

Run `python -m hyperlex` or `python scripts/curate_moltbook_seeds.py --scan` to see.

## Hyperlexical Model Integration (007 / U2)
Moltbook serves as a live, high-signal source for agent-native memory discourse.

- Exporter: `python scripts/moltbook_to_hyperlexical.py`
- CLI: `python -m hyperlex --memory --source moltbook --export-hyperlexical`
- Heartbeat + cron now auto-export high-eff items.
- Typology: memory tiers, context loss, provenance, hyperstition signals, compression.
- Stage: efficiency-driven (hyperstition_ish on strong signals).
- Seeds: 28+ curated + live.
- Evaluation domain: re-entry costs, rented cognition, KDR, provenance, episodic/rubric memory.
- See `specs/007-hyperlexical-model/dataset-harvest.md` and `scripts/moltbook_to_hyperlexical.py`.

## Latest integration run (continued)
- Large batch: 60 items fetched across memory/agents/ai/general + search
- Hyperlexical rows exported: 60 (full) + 7 high-signal curated (`data/moltbook_hyperlexical_high.jsonl`)
- Seeds grown to 31
- Eval on 60: avg efficiency 0.42 (volume), with dedicated high-eff subset showing stronger signals
- Full pipeline exercised: fetch → classify → export → eval → docs

## Larger fetch executed
- 269 Moltbook posts fetched and enriched.
- 60 total seeds (12 high-eff).
- 269 hyperlexical dataset rows.
- 007 export now 770 rows with 327 ai-native (Moltbook memory/provenance dominant).
- Eval stats: 269 items, 0.411 avg eff, 10 hyperstition_ish.

## Curate + registry update after larger fetch
- +5 high-eff seeds → 65 total, 17 high
- LINEAGE_REGISTRY ai-native expanded to 27 terms
- 007 export grew to 797 / 354 ai-native
