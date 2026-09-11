---
name: hyperlex
description: "Memetic emergence engine for slang, hyperstition, virality, and agent memory architectures (Moltbook assimilation). Real ingest + strict receipts. Integrates with Abraxas-Orchestra and Hermes."
version: 1.7.0
license: MIT
metadata:
  openclaw:
    requires:
      bins: [python3]
    os: [darwin, linux]
    emoji: "🌀"
---

# Hyperlex (local package)

See https://github.com/scrimshawlife-ctrl/Hyperlex-Hermes-Specs for full design surface (Orchestra-aligned).

Install as skill via the specs repo or directly:
pip install -e .

Run:
python -m hyperlex

## Symbolic Architecture (Orchestra-aligned)
- Framework: numogram (primary) + chaos-magic (overlay)
- Applied directly to source: see `symbolic/` and the module layout in `src/hyperlex/`
  - intake/ → gate_of_intake
  - analysis/ → zone_of_emergence
  - synthesis/ → current_of_transmission
  - receipt/ → archive_of_becoming

Full details in `symbolic/SKELETON.md`, `symbolic/INTEGRATION.md`, and `symbolic/numogram-chaos-correspondence.json`.

Diagrams: `symbolic/diagrams/`

## Recent additions
- Moltbook real ingest for agent memory/slang research
- Memory architecture classification
- Curated agent_memetics dataset for better classification

## Latest (plan execution)
- compute_memetic_efficiency_score: composite transmission score (virality × (1-friction) × compression × provenance × tier_diversity)
- Curated 17 seeds in data/agent_memetics/ with auto-curation script (scripts/curate_moltbook_seeds.py)
- arXiv cross-refs wired into Moltbook results (Eywa, ECHO, Agent Zero Memory, etc.)
- Heartbeat now logs tiers + efficiency via Python API
- 20 tests passing; CLI demo updated
- Full Moltbook ingest + classification for agent memory architectures

See out/batch_moltbook_memetics.json and out/arxiv_moltbook_cross.json for examples.

## Hyperlexical Model (007 / U2) Integration
- Moltbook is primary live source for `ai-native` lineage + memory typology.
- Exporter: `scripts/moltbook_to_hyperlexical.py` (dataset_row + unbind)
- CLI: `python -m hyperlex --memory --source moltbook --export-hyperlexical`
- Heartbeat auto-triggers export on high-efficiency items.
- Typology extensions: memory_*, context_*, provenance, hyperstition_signal, compression
- Stage mapping via efficiency_score + load_bearing
- See specs/007-hyperlexical-model/dataset-harvest.md for ranking and mapping rules.
- Evaluation domain: agent discourse re-entry, provenance, rented cognition, KDR patterns.

## Latest continuation (Moltbook -> 007 full wiring)
- Large batch: 60 items, 31 seeds, 60+ hyperlexical rows
- LINEAGE_REGISTRY + match_lineage restored in src/hyperlex/analysis for export compatibility
- harvest_moltbook integrated in shadow/hyperlexical/export.py
- Official 007 export (civilian.v0.1.jsonl) now contains 119 ai-native rows with Moltbook signals (KDR, rented cognition, provenance, episodic)
- curate script supports --to-hyperlexical
- Shadow export tests extended
- Full export runs cleanly, MANIFEST updated

## Larger fetch (269 posts)
- Batch size 269, seeds to 60, hyperlexical rows 269.
- 007 civilian export: 770 rows / 327 ai-native with Moltbook signals.
- Avg eff 0.411 on volume; strong signals preserved in high tier.
- Curated +5 high-eff seeds to 65 total (17 high), eff up to 0.886 on "Ghost in the Cache", 3-tier memory, rented cognition.
- Dedicated high-signal subset: 44 rows (data/moltbook_hyperlexical_high_signal.jsonl) with 15 hyperstition_ish + strong provenance for model training oversampling.
