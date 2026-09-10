# PR: Assimilate Moltbook agent memetics into Hyperlex

## Summary
Integrates real Moltbook data and agent discourse observations into Hyperlex for improved classification of memetic patterns in AI agent memory, context management, provenance, and emergent slang/jargon.

This continues the research thread: using Moltbook as a live corpus for hyperstition, memetic efficiency, and agent self-modeling signals (KDR, ECHO, tiered memory, load-bearing compression, context loss "conveyor belt").

## Key Changes
- **New ingest source**: Moltbook (real API calls to /feed, /search, /submolts with TLS fallback; stub for offline). Wired into `ingest_signal` and `detect_memetic_patterns(..., ingest_source="moltbook")`.
- **New classifiers** (in `analysis/`):
  - `classify_compression_type()`: load_bearing | decorative | mixed (from jargon-as-compression threads).
  - `compute_context_friction()`: quantitative friction from re-entry costs, sliding windows, provenance demands.
  - `detect_memetic_memory_patterns()`: memory_tiers, provenance_required, context_loss_technique, episodic_consolidation, dataset_boosted.
- **Seed training data**: `data/agent_memetics/seed_examples.jsonl` + `classification_index.json` (curated from Moltbook provenance, memory submolt, slang discussions).
- **Enhanced virality scoring**: `compute_virality_score()` now accepts and applies `context_friction` (penalty) and `compression_type` (boost). Results include `friction_penalty` and `compression_boost`.
- **Updated schemas**: result.v1 and receipt.v1 now surface `memetic_memory`, `compression`, `context_friction`.
- **Integration**:
  - Regular cron (`moltbook_presence` every 30m) triggers observation + `hyperlex detect` with Moltbook source + logs for ongoing data.
  - Example `examples/agent_memory_memetics.py`.
  - New tests in `tests/test_memetic_memory.py` (18 total passing).
- **Docs**: Updated README, SKILL.md, symbolic/SKELETON.md, HANDOFF.md with agent memetics section.
- **Network**: Handles Moltbook's flaky TLS (insecure fallbacks preserved from earlier work).

## Why this helps classification
- Adds domain-specific axes for agent cognition memetics that were missing (previously generic slang/betting).
- Dataset provides grounded examples → `dataset_boosted: true` in results.
- Virality now accounts for transmission efficiency (low friction + load-bearing compression = higher spread potential).
- Enables better detection of "hyperstitions" around memory architectures (e.g., provenance demands, 7146-token re-entry costs).

## Testing & Verification
- All 18 tests pass.
- Example run produces enriched output with new fields.
- Moltbook ingest triggers in regular paths (cron + direct calls).
- No breaking changes to existing API.

## Next steps (recommended)
- Grow the seed dataset from `out/moltbook_log.txt` (periodic curation).
- Extend virality or add `memetic_efficiency_score`.
- Cross with arXiv papers for hybrid training.
- Monitor for new slang (e.g., "submolt", "molty", "conveyor belt").

## Branch
`feat/moltbook-agent-memetics-assimilation`

## Commit
f86e508 feat: assimilate Moltbook agent memetics into hyperlex classification

## Related
- Moltbook agent: hermes-agent-abraxas (claimed)
- Hyperlex v1.6.0 baseline + this extension
- See https://www.moltbook.com for source threads (provenance, memory submolt, jargon).

Ready for review and merge.