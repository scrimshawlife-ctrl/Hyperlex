# Design: analysis enrichment + attractor store (Hyperlex-native)

**Date:** 2026-08-06  
**Status:** Complete (schema + builder + wiring + attractor store)  
**Version target:** 0.4.x (additive)  

## Intent

Extend Hyperlex analysis results with optional compression metrics, typology-aligned tags, propagation tags, and a compact O/I/S summary — without importing external system vocabulary or governance lanes.

## Surfaces

1. **Schema** — optional fields under `analysis` + optional `provenance.seed` (integrity note)
2. **Builder** — `src/hyperlex/analysis/signal_report.py`
   - `compression_metrics` from existing virality/memetics/lineage
   - `symbolic_role` values = Hyperlex typology IDs + drivers (not external role labels)
   - `propagation_vector` platform tags
   - `signal_report` compact O/I/S summary
   - `build_integrity_header` (alias: `build_seed_header`)
3. **Call-site** — wired in `detect_memetic_patterns`
4. **Attractor store** — `src/hyperlex/signals/` → `~/.hyperlex/signals/inbox.jsonl`
5. **Rune** — `RUNE.HLX.ATTRACTOR_CANDIDATE` (role: attractor, authority: advisory)
6. **CLI** — `hyperlex inbox list|push|clear`; `relay --push-inbox`

## Operator usage

```bash
python -m hyperlex analyze "sharp money" --relay
python -m hyperlex relay --input result.json --push-inbox
python -m hyperlex inbox list
```

## Invariants

- `provenance.brier` remains `null` on open analysis
- All new fields optional and fail-open
- Offline-first; no external package import
- Attractor candidates are advisory; operator review before settlement or registry change

## Terminology notes

| Avoided (external) | Native Hyperlex |
|--------------------|-----------------|
| SHADOW / capability_lane | attractor candidate / authority: advisory |
| SEED governance block | integrity header (method, risk_band, authority) |
| Companion role labels (Irony Shield, …) | typology IDs + drivers already in memetics |
| Canon binding language | operator review before settlement / registry change |

## Remaining (optional)

1. Enrich `scan` with focus / time_window / min_virality
2. Daily aggregate forage receipt
