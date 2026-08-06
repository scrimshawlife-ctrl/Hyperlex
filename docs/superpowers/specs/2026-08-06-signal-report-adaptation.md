# Design: SIGNAL REPORT parity (Companion process adaptation)

**Date:** 2026-08-06  
**Status:** Schema landed · analysis population pending  
**Version target:** 0.4.x (additive)  

## Source

Abraxas Companion deep Hyperstition / Memetic Emergence Scan (LIVE_EMERGENCE_SCAN + full SIGNAL REPORT + Notion inbox + SHADOW rune proposals + SEED governance).

## What was adapted into Hyperlex

1. **Schema (`schemas/result.v1.schema.json`)** — optional fields:
   - `provenance.seed` — SEED-style integrity header (status, determinism, entropy_class, capability_lane)
   - `analysis.compression_metrics` — semantic / emotional / virality / identity / efficiency / drift
   - `analysis.symbolic_role` — multi-select roles
   - `analysis.propagation_vector` — platform / demographic tags
   - `analysis.slang_family_tree` — compact lineage tree
   - `analysis.signal_report` — human-facing summary (observed / inferred / speculative + generated_mutations + actionable_recommendations)
   - `analysis.mutation_prediction` already present (aligned)

2. **Invariants preserved**
   - `provenance.brier` remains `null` on open analysis
   - All new fields optional and fail-open
   - Offline-first; no Abraxas hard dependency
   - Generated mutations / next forms stay SPECULATIVE

## Remaining implementation (ordered)

1. Populate the new fields inside `detect_memetic_patterns` / analysis core from existing virality, memetics, hyperstition, lineage, and mutation blocks.
2. Optional local signals inbox (`~/.hyperlex/signals/` or `inbox` CLI) for high-priority attractors.
3. Enrich `scan` / live routes with focus + time_window + min_virality parameters matching Companion multi-tool pattern.
4. Emit optional SHADOW `rune_candidate` envelopes on high hyperstition stage (via existing relay / rune_envelope).
5. Forage / daily aggregate receipt that can correct prior “quiet” assessments.

## Success criteria

- Offline `pipeline "rizz"` (or demo) can carry non-empty `compression_metrics` + `symbolic_role` when data supports it.
- Schema validates; existing golden receipts still pass (new fields absent = fine).
- No numeric Brier introduced on open analysis.

## References

- Companion SIGNAL REPORT structure (OBSERVED / INFERRED / SPECULATIVE + COMPRESSION METRICS + SYMBOLIC ROLE + PROPAGATION VECTOR + GENERATED MUTATIONS + SLANG FAMILY TREE)
- Mutation prediction design (same day)
- Hyperlex hard rules: settled Brier only, Phase 5 SPECULATIVE, no Abraxas import
