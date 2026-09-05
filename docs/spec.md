# Hyperlex Technical Specification v0.3

**Hermes skill (Python package repo).** No hard dependency on Abraxas. Relevant Abraxas wire
capabilities are Hyperlex modules under `hyperlex.compat.abraxas`.

API freeze: [`docs/api-v1.md`](api-v1.md) · `hyperlex.API_V1` (unchanged in 0.3.x)  
Extended: `hyperlex.API_EXTENDED` (additive; includes Phase 5 simulation)

## Runtime API

### Ingest & analysis
- `ingest_signal(query: str, source: str = "mock") -> str`
- `fetch_ingest(query, source="mock", structured=True, max_terms=8) -> dict`
- `detect_memetic_patterns(query=..., ingest_source="mock", ...) -> dict`
- `match_lineage(text, terms=None, min_confidence=0.42, registry=None) -> dict | None`
- `compute_lineage_confidence(hits, family_terms, corpus) -> (float, dict)`

### Receipts
- `emit_receipt(result, out_dir=None, validate=True, append_ledger=True, ledger_path=None) -> Path`
- `verify_receipt(payload) -> (bool, str)`

### Calibration
- `extract_forecasts(result, receipt_ref=None) -> list[dict]`
- `settle` / `score_pair` / `score_series` / `settle_and_log` / `recompute_series`
- `NOT_COMPUTABLE`

### Relay
- `relay_from_result` / `relay_forecasts` / `relay_series` / `list_runes`

### Lineage backfill (0.2.12+)
- `apply_backfill` / `inventory_backfill` / `list_backfill_packs` / `backpropagate_lineage`

### Phase 5 simulation (0.3.0+)
- `simulate_cultural_transmission(seed_term, ...) -> dict` — multi-community cascade
- `run_multi_agent_memetics(seed_term, ...) -> dict` — role lattice adoption
- `forecast_hyperstition_risk(...)` / `risk_from_analysis(result, ...)`
- `build_family_phylogeny(family_id)` / `list_phylogeny_families()`
- `run_phase5_scenario(seed_term, ..., analysis_result=None) -> dict`

All Phase 5 packets set `brier: null` and `provenance: SPECULATIVE` (phylogeny: INFERRED structure).

### Compat (optional host import)
```python
from hyperlex.compat.abraxas import (
    to_brier_ledger_entry,
    to_brier_score_packet,
    to_operator_brier_review,
    list_hlx_runes,
    envelopes_from_result,
    CLAIM_LABELS,
)
```

## Sources

`mock`, `real`, `glossary`, `glossary_expanded`, `web`, `reddit`, `urban`,
`wikipedia`, `x_search`, `firecrawl`, `crawl4ai`, `combined`

## Command surface

### Hermes skill CLI (`scripts/hyperlex.py`)
```bash
check | doctor | sources | ingest | analyze | scan | relay
extract-forecasts | settle | score-series | verify-score-log
emit-receipt | list-receipts | ledger-stats | ledger-diff | archive-export
lineage-backfill | lineage-backprop
simulate          # Phase 5
diagram | signal | feedback | validate | verify-receipt | smoke
```

### Package CLI
```bash
python -m hyperlex check|analyze|scan|relay|settle|score-series|simulate|version
```

## Output contracts

### Analysis result
- `observed`, `inferred`, `speculative`
- `provenance.brier` always `null` on open analysis
- `analysis`: neologisms, virality, memetics, hyperstition, optional lineage

### Phase 5 scenario
- schema `hyperlex.phase5_scenario.v1`
- nested: transmission, multi_agent, hyperstition_risk, optional phylogeny
- `brier: null` at every level

### Calibration
- Forecasts never attach Brier; settlements + series after operator decision

## Error handling

- Ingest failures degrade; do not crash
- Missing settlements → `NOT_COMPUTABLE`
- Simulation is deterministic for fixed params (no RNG in 5.0)
