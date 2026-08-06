# Design: SIGNAL REPORT parity (Companion process adaptation)

**Date:** 2026-08-06  
**Status:** Schema + builder landed · call-site wiring next  
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

3. **Invariants preserved**
   - `provenance.brier` remains `null` on open analysis
   - All new fields optional and fail-open
   - Offline-first; no Abraxas hard dependency

## Remaining implementation (ordered)

1. **Wire into `detect_memetic_patterns`** (one import + two calls):

```python
from .signal_report import attach_signal_report_fields, build_seed_header

# after mutation_prediction / vector_neighbors block, before result = {...}:
attach_signal_report_fields(
    analysis,
    observed=observed,
    inferred=inferred,
    speculative=speculative,
    recommendation=(
        "Bind RUNE.HLX.COMMUNICATION_RELAY via hyperlex.relay; "
        "extract_forecasts for calibration; cron LIVE_EMERGENCE_SCAN."
    ),
    ingest_source=ingest_source,
)

# inside result["provenance"]:
"seed": build_seed_header(
    ingest_source=ingest_source,
    hyper_stage=hyper.get("loop_stage"),
),
```

2. Optional local signals inbox (`~/.hyperlex/signals/` or `inbox` CLI).
3. Enrich `scan` / live routes with focus + time_window + min_virality.
4. Emit optional SHADOW `rune_candidate` envelopes on high hyperstition stage.
5. Forage / daily aggregate receipt.

## Success criteria

- Offline `pipeline "rizz"` carries non-empty `compression_metrics` + `symbolic_role`.
- Schema validates; existing golden receipts still pass.
- No numeric Brier on open analysis.

## References

- Companion SIGNAL REPORT structure
- Mutation prediction design (same day)
- Hyperlex hard rules: settled Brier only, Phase 5 SPECULATIVE, no Abraxas import
