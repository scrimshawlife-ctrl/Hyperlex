# Phase 5 — Research simulation track

Phase 5 extends Hyperlex beyond detect → receipt → settle into **research-grade
simulation** of cultural transmission, multi-agent adoption, hyperstition risk,
and lightweight phylogenies.

## Scope (v0.3.0 / Phase 5.0)

| Capability | Status |
|------------|--------|
| Cultural transmission cascade | Ready (`simulate --mode transmission`) |
| Multi-agent memetic roles | Ready (`simulate --mode agents`) |
| Hyperstition risk forecasting | Ready (`simulate --mode risk`) |
| Phylogeny scaffold | Ready (`simulate --mode phylogeny`) |
| Domain phylogeny packs | Ready (`data/phylogeny/` · `--domain finance|ai-native|political|regional`) |
| Hybrid lineage re-rank | Ready (lexical + vector boost) |
| Scenario library / compare | Ready (`simulate --mode compare`) |
| Research export | Ready (`simulate --mode export`) |
| Composed scenario | Ready (`simulate --mode scenario`) |
| Transmission calibration vs settled series | Ready (`simulate --mode calibrate`) |
| Risk-tier → scan/cron schedule | Ready (`risk-schedule` / `simulate --mode schedule`) |
| Open research publications | Ongoing (export + docs; external writeups separate) |

## Non-goals

- **Not** market advice or auto-trading
- **Not** Brier without settlement
- **Not** rewriting historical receipts
- **Not** Abraxas hard dependency

## Operator entry

```bash
# Single atomic term
python3 scripts/hyperlex.py simulate --term rizz --domain ai --out out/phase5/rizz.json

# Multi-term free text → auto-expands to separate scenarios (not one blended seed)
python3 scripts/hyperlex.py terms-split "sigma rizz locked in"
python3 scripts/hyperlex.py simulate --term "sigma rizz locked in" --domain ai
# → schema hyperlex.phase5_multi_term.v1 with terms [sigma, rizz, locked in]

# Force a single blended seed only if intentional
python3 scripts/hyperlex.py simulate --term "sigma rizz locked in" --no-expand
```

Details: [modules/simulation.md](modules/simulation.md).

### Atomic terms

Backfill packs store **one term per entry**. Phrases like `locked in` are one atom;
`sigma` and `rizz` are separate. Concatenating them for a Phase 5 run was a demo
mistake — the engine now expands by default.

**Expanded demos (Pages):** [demos/atomic-terms.md](demos/atomic-terms.md) · fixtures in `examples/demos/`.

## How it sits on the stack

```text
intake → analysis (lineage, virality, hyperstition stage)
       → Phase 5 scenario (transmission + agents + risk + phylogeny)
       → optional archive / diagram / relay
       → calibration only if operator settles forecasts
```

Phase 5 outputs stay under **SPECULATIVE**. Open analysis still has `provenance.brier = null`.

## Pages history

Sanitized Phase 5 digests can be appended to the static run history:

```bash
python3 scripts/hyperlex.py simulate --term rizz --out /tmp/p5.json
python3 scripts/hyperlex.py archive-export --phase5 /tmp/p5.json --history --snapshot-id "phase5-$(date -u +%Y%m%dT%H%M%SZ)"
```

See [Run history catalog](archive/index.md).
