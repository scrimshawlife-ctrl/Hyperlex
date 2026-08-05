# Phase 5 — Simulation & hyperstition risk

**Status:** Phase 5.0 (v0.3.0)  
**Label:** All simulation outputs are **SPECULATIVE**  
**Hard rule:** `brier` is always `null` — never invent scores; never auto-settle.

## Modules

| Module | Schema | Role |
|--------|--------|------|
| `simulate_cultural_transmission` | `hyperlex.cultural_transmission.v1` | Multi-community cascade with decay |
| `run_multi_agent_memetics` | `hyperlex.multi_agent_memetics.v1` | Role lattice (innovator → amplifier) |
| `forecast_hyperstition_risk` | `hyperlex.hyperstition_risk.v1` | Composite risk tier for real-world systems |
| `build_family_phylogeny` | `hyperlex.phylogeny.v1` | Lightweight family tree scaffold |
| `run_phase5_scenario` | `hyperlex.phase5_scenario.v1` | Compose all of the above |

Package path: `hyperlex.simulation`.

## Cultural transmission

Discrete-time adoption across abstract communities (`origin_niche` → `archive_residual`).  
Effective β scales with virality hybrid. Resistance rises toward institutional slots.

```bash
python3 scripts/hyperlex.py simulate --mode transmission --term rizz --virality 0.7
```

## Multi-agent memetics

Agents: `innovator`, `early_adopter`, `mainstream`, `skeptic`, `amplifier`.  
Exposure accumulates from adopted agents’ broadcast weights; adopt when exposure ≥ role threshold.

```bash
python3 scripts/hyperlex.py simulate --mode agents --term "locked in" --agents 24
```

## Hyperstition risk

Composes stage, virality, lineage, memetic score, optional transmission/agent summaries  
into `risk_score` + `tier` (`LOW` | `MODERATE` | `ELEVATED` | `CRITICAL`).

```bash
python3 scripts/hyperlex.py simulate --mode risk --from-analyze --term "sharp money" --domain markets
```

Domains: `general`, `markets`, `ai`, `politics` (notes only; score drivers are shared).

## Phylogeny scaffold

Not a full linguistic phylogeny — registry terms + optional backfill `first_seen_month` as a tree for research / diagrams.

```bash
python3 scripts/hyperlex.py simulate --mode phylogeny --family brainrot-aura
```

## Full scenario

```bash
python3 scripts/hyperlex.py simulate --term "sigma rizz" --mode scenario --domain ai --out out/phase5/scenario.json
python3 scripts/hyperlex.py simulate --from-analyze --term "agentic slop" --domain ai --verbose
```

## Transmission calibrate (0.3.6)

Advisory β/γ grid-search against settled pairs. **SPECULATIVE** — not Brier.

```bash
python3 scripts/hyperlex.py simulate --mode calibrate
```

## Scenario library + compare

```bash
python3 scripts/hyperlex.py simulate --mode compare --list-scenarios
python3 scripts/hyperlex.py simulate --mode compare --term "rizz"
python3 scripts/hyperlex.py simulate --mode compare --scenario viral_cascade --term "rizz"
```

## Research export

```bash
python3 scripts/hyperlex.py simulate --mode export --term "rizz" --export-dir out/research
```

## Risk → scan schedule (0.3.7)

Advisory mapping from hyperstition risk tier to LIVE_EMERGENCE_SCAN cadence and
Hermes cron job envelopes. **Does not auto-register** cron jobs.

```bash
python3 scripts/hyperlex.py risk-schedule --list-tiers
python3 scripts/hyperlex.py risk-schedule --tier ELEVATED --schedule-out /tmp/hlx-cron
python3 scripts/hyperlex.py simulate --mode schedule --term "rizz" --domain ai
```

API: `plan_scan_from_risk`, `plan_scan_from_term`, `plan_scan_from_tier`,
`write_scan_plan`, `aggregate_scan_risk`, `TIER_POLICY`.

Post-scan: `scan` attaches `scan_risk_advisory` from lineage coverage.

## Multi-term seeds (0.3.9)

Free-text seeds that contain multiple lexicon atoms expand automatically:

```bash
python3 scripts/hyperlex.py terms-split "sigma rizz locked in"
# → ["sigma", "rizz", "locked in"]

python3 scripts/hyperlex.py simulate --term "sigma rizz locked in" --domain ai
# → hyperlex.phase5_multi_term.v1  (one scenario per atom)

python3 scripts/hyperlex.py simulate --term "sigma rizz locked in" --no-expand
# → single blended scenario (opt-in only)
```

API: `split_seed_terms`, `run_phase5_multi_term`, `run_phase5_scenario(..., expand_terms=True)`.

## Integrity

1. Simulation does **not** rewrite receipts or ledgers.
2. Simulation does **not** write score-log settlements.
3. Use `extract_forecasts` + operator `settle` if you want Brier later.
4. Treat tiers as research signals for scan frequency and archival diligence — not market advice.
5. Independent lexicon atoms are never density-stacked into one primary lineage when multi-term.

## Research lineage

Distilled (not reimplemented) from arXiv concepts already listed in DESIGN:

- Cultural transmission (2203.00715)
- Virality / diffusion (2510.05761)
- Hyperstition loops (2410.23794)
- Memetics protocol (2407.11861)
