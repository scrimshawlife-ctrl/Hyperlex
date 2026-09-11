---
name: hyperlex
description: "Memetic emergence engine for slang, hyperstition, virality, and agent memory architectures (Moltbook assimilation). Real ingest + strict receipts. Integrates with Abraxas-Orchestra and Hermes."
version: 1.5.0
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

## Latest (continued)
- compute_memetic_efficiency_score: composite transmission score (virality × (1-friction) × compression × provenance × tier_diversity)
- Curated 17 seeds in data/agent_memetics/ with auto-curation script (scripts/curate_moltbook_seeds.py)
- arXiv cross-refs wired into Moltbook results (Eywa, ECHO, Agent Zero Memory, etc.)
- Heartbeat now logs tiers + efficiency via Python API
- 20 tests passing; CLI demo updated
- Full Moltbook ingest + classification for agent memory architectures

See out/batch_moltbook_memetics.json and out/arxiv_moltbook_cross.json for examples.
