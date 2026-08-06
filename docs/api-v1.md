# Hyperlex Public API v1 (frozen)

Hyperlex is a **Hermes skill** implemented as a Python package. No Abraxas, Orchestra, or Hollersports
import is required at runtime.

`API_V1` remains frozen through **0.3.x**. Phase 5 simulation symbols are **additive** on
`API_EXTENDED` only.

## Package entry

```python
import hyperlex
from hyperlex import (
    ingest_signal,
    fetch_ingest,
    detect_memetic_patterns,
    match_lineage,
    emit_receipt,
    extract_forecasts,
    settle,
    score_pair,
    score_series,
    settle_and_log,
    recompute_series,
    relay_from_result,
    list_runes,
    NOT_COMPUTABLE,
    PKG_VERSION,
)
```

`hyperlex.API_V1` is the frozen symbol tuple. Semver **0.2.x / 0.3.x** will not remove or
rename these symbols. New symbols may be added on `API_EXTENDED`; breaking changes wait for 1.0
or an explicit deprecation window.

## Stable call contracts

| Symbol | Contract |
|--------|----------|
| `ingest_signal(query, source="mock")` | `str` signal |
| `fetch_ingest(query, source="mock", ...)` | structured ingest + `source_fingerprint` |
| `detect_memetic_patterns(...)` | result dict; `provenance.brier` is always `null` |
| `emit_receipt(result, ...)` | writes receipt JSON; optional ledger append |
| `extract_forecasts(result)` | list of forecasts; **no** Brier field |
| `settle` / `score_pair` / `score_series` | Brier only after settlement; else `NOT_COMPUTABLE` |
| `relay_from_result(result)` | `RUNE.HLX.*` envelopes |

## CLI (Hermes skill)

Hermes skill tree:

```bash
python3 scripts/hyperlex.py <command>
```

Installed package:

```bash
python -m hyperlex <command>
# or console script: hyperlex <command>
```

Core commands: `check`, `sources`, `ingest`, `analyze`, `scan`, `relay`,
`extract-forecasts`, `settle`, `score-series`, `emit-receipt`, `list-receipts`,
`verify-receipt`, `verify-receipt-ledger`, `verify-score-log`, `smoke`,
`lineage-backfill`, `lineage-backprop`, `simulate` (Phase 5), `archive-export`, `diagram`,
`vector-seed` / `vector-search` / `vector-stats` / `vector-export` / `vector-import` / `vector-sync`
(SQLite · local Chroma · Cloud promote — see [modules/vectordb.md](modules/vectordb.md)).

### Phase 5 extended API (0.3.0+)

```python
from hyperlex import (
    simulate_cultural_transmission,
    run_multi_agent_memetics,
    forecast_hyperstition_risk,
    risk_from_analysis,
    build_family_phylogeny,
    run_phase5_scenario,
)
```

All return packets with `brier: null` and research provenance — never settled scores.

## Abraxas-compatible modules (optional host import)

Hosts (including Abraxas) import **from Hyperlex**, not the reverse:

```python
from hyperlex.compat.abraxas import (
    to_brier_ledger_entry,   # BrierLedgerEntry.v1
    to_brier_score_packet,   # BrierScorePacket.v1
    to_operator_brier_review,
    list_hlx_runes,
    envelopes_from_result,
    CLAIM_LABELS,
    NOT_COMPUTABLE,
)
```

These are pure Hyperlex implementations of the **relevant** Abraxas wire shapes
(Brier ledger/score, operator review, claim labels, HLX runes). They do not load
Abraxas.

## Explicit non-goals of API v1

- Public PyPI release requirement
- Hard dependency on Abraxas runtime
- Emitting numeric Brier on open analysis
- Autonomous calibration mutation
