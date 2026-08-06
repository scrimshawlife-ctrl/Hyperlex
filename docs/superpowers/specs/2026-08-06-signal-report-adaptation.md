# Design: SIGNAL REPORT parity (Companion process adaptation)

**Date:** 2026-08-06  
**Status:** Schema + builder + wiring + signals inbox + SHADOW candidate complete  
**Version target:** 0.4.x (additive)  

## Source

Abraxas Companion deep Hyperstition / Memetic Emergence Scan (LIVE_EMERGENCE_SCAN + full SIGNAL REPORT + Notion inbox + SHADOW rune proposals + SEED governance).

## What was adapted into Hyperlex

1. **Schema** — optional SIGNAL REPORT fields + `provenance.seed`
2. **Builder** — `src/hyperlex/analysis/signal_report.py`
3. **Call-site** — wired into `detect_memetic_patterns`
4. **Signals inbox** — `src/hyperlex/signals/` → `~/.hyperlex/signals/inbox.jsonl`
5. **SHADOW candidate** — `RUNE.HLX.SHADOW_CANDIDATE` in relay catalog + schema enum
6. **CLI** — `hyperlex inbox list|push|clear`; `relay --push-inbox`

## Operator usage

```bash
# Analyze with relay (SHADOW envelope when stage is EMERGENT/ACTUALIZING)
python -m hyperlex analyze "sharp money" --relay

# Relay + auto-push to local inbox
python -m hyperlex relay --input result.json --push-inbox

# Inbox surface
python -m hyperlex inbox list
python -m hyperlex inbox push --input result.json --force
python -m hyperlex inbox clear --dry-run
```

## Invariants preserved

- `provenance.brier` remains `null` on open analysis
- All new fields optional and fail-open
- Offline-first; no Abraxas hard dependency
- SHADOW is advisory only; human sovereignty required before any canon binding

## Remaining (optional)

1. Enrich `scan` / live routes with focus + time_window + min_virality
2. Forage / daily aggregate receipt that can correct prior “quiet” assessments

## References

- Companion SIGNAL REPORT structure
- Hyperlex hard rules: settled Brier only, Phase 5 SPECULATIVE, no Abraxas import
