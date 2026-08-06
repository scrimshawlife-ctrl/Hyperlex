# Design: SIGNAL REPORT parity (Companion process adaptation)

**Date:** 2026-08-06  
**Status:** Schema + builder + call-site wiring complete  
**Version target:** 0.4.x (additive)  

## Source

Abraxas Companion deep Hyperstition / Memetic Emergence Scan (LIVE_EMERGENCE_SCAN + full SIGNAL REPORT + Notion inbox + SHADOW rune proposals + SEED governance).

## What was adapted into Hyperlex

1. **Schema (`schemas/result.v1.schema.json` + package-local)** — optional fields:
   - `provenance.seed` — SEED-style integrity header
   - `analysis.compression_metrics`
   - `analysis.symbolic_role`
   - `analysis.propagation_vector`
   - `analysis.slang_family_tree`
   - `analysis.signal_report`
   - `analysis.mutation_prediction` (already present)

2. **Builder module** — `src/hyperlex/analysis/signal_report.py`
   - `build_compression_metrics`
   - `build_symbolic_roles`
   - `build_propagation_vector`
   - `build_signal_report`
   - `attach_signal_report_fields(analysis, ...)` — fail-open mutator
   - `build_seed_header`

3. **Call-site** — `detect_memetic_patterns` now:
   - imports the helpers
   - calls `attach_signal_report_fields(...)` after mutation / vector blocks
   - attaches `provenance.seed` via `build_seed_header(...)`

4. **Invariants preserved**
   - `provenance.brier` remains `null` on open analysis
   - All new fields optional and fail-open
   - Offline-first; no Abraxas hard dependency

## Remaining (optional next tranche)

1. Local signals inbox (`~/.hyperlex/signals/` + thin `inbox` CLI)
2. Enrich `scan` / live routes with focus + time_window + min_virality
3. Emit optional SHADOW `rune_candidate` envelopes on high hyperstition stage
4. Forage / daily aggregate receipt

## Success criteria (met for core path)

- Offline `pipeline "rizz"` / `analyze` carries non-empty `compression_metrics` + `symbolic_role` + `signal_report` when data supports it.
- Schema validates; existing golden receipts still pass (new fields absent = fine).
- No numeric Brier on open analysis.

## References

- Companion SIGNAL REPORT structure
- Mutation prediction design (same day)
- Hyperlex hard rules: settled Brier only, Phase 5 SPECULATIVE, no Abraxas import
