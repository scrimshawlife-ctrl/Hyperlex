# Operator loop (recommended)

**Goal:** settle a few real forecasts and get honest Brier — not more simulators.

The backend is **automatic**. One command runs ingest through results. Settlement
is the only step that stays human.

## Posture

| Do | Defer |
|----|--------|
| `pipeline` / `ingest` / `run` for full results | Manual analyze→receipt chaining |
| Atomic seeds (or bags that auto-expand) | Blended multi-term seeds |
| `pending` → `settle` → `score-series` | Invented Brier |
| MODERATE offline cron when ready | Auto-mutating Hermes cron |
| | ANN until corpus is large |

See [commands.md](commands.md) · [demos/atomic-terms.md](demos/atomic-terms.md).

## Daily path (simplified) — automatic backend

```bash
export HERMES_SKILL_DIR="${HERMES_SKILL_DIR:-$HOME/.hermes/skills/hyperlex}"
HLX="python3 $HERMES_SKILL_DIR/scripts/hyperlex.py"

# See the map anytime
$HLX commands

# AUTO: ingest → analyze → receipt → forecasts → score log → Phase 5 risk
# Same for: pipeline | run | ingest  (ingest --raw-only = signal only)
$HLX pipeline "rizz" --route offline
$HLX ingest "locked in"                 # full results by default
$HLX pipeline "sigma rizz locked in"    # expands to 3 atom results automatically

# Multi-query cron shape (atomic pack; offline-safe)
$HLX scan --config "$HERMES_SKILL_DIR/examples/cron/scan-queries.json" \
  --route offline --receipt --forecasts --append-log

# When network is allowed
$HLX pipeline "agentic slop" --route live
```

### Ingest routing (prefer routes over adapter names)

| Route | Resolves to | Network |
|-------|-------------|---------|
| `offline` / `mock` / `default` | `mock` | no |
| `live` | `combined` | yes |
| `glossary` | `glossary` | yes |
| `social` | `x_search` | yes |

Aliases still work (`real`→glossary, `x`→x_search, `firecrawl`→crawl4ai).
`HYPERLEX_OFFLINE=1` forces mock for any network source.

```bash
$HLX sources
$HLX sources --route live          # preview resolve
$HLX ingest "rizz" --route offline
$HLX analyze "rizz" --route offline
```

## Calibration path (where Brier appears)

```bash
$HLX pending                       # open forecasts in score log
$HLX settle --forecast-id <id> --decision TRUE   # or FALSE / VOID
$HLX score-series --mean-shift --verify-chain
```

Rules:

- Open analysis always has `provenance.brier = null`
- Empty series → `NOT_COMPUTABLE`
- Never invent Brier from Phase 5 or scan advisories

## Cron / risk tier (advisory)

```bash
$HLX risk-schedule --tier MODERATE --schedule-out /tmp/hlx-cron
# Operator pastes job into Hermes — Hyperlex never auto-registers
```

Scan summaries include `scan_risk_advisory` (lineage coverage → suggested next
cadence). Re-run `risk-schedule` before changing live jobs.

See [cron-live-emergence.md](cron-live-emergence.md).

## Vector index (tied to ingest · optional bulk)

**Automatic (local):** after each `pipeline` / `run` / `ingest` unit, Hyperlex
fail-open indexes terms + receipt into the local vector store when
`HYPERLEX_VECTOR` is on (default **auto** if a store already exists). Set
`HYPERLEX_VECTOR=1` and optionally `HYPERLEX_VECTOR_BACKEND=chroma` to always
keep local Chroma warm on every ingest.

```bash
export HYPERLEX_VECTOR=1
export HYPERLEX_VECTOR_BACKEND=chroma
export HYPERLEX_CHROMA_PATH=~/.hyperlex/chroma
$HLX pipeline "rizz" --route offline   # also steps: vector_index
```

**Bulk backfill** (registry + YTD packs + all receipts) still uses seed:

```bash
$HLX vector-seed --backend chroma --db ~/.hyperlex/chroma \
  --through 2026-08 --include-home --include-golden
$HLX vector-stats --backend chroma --db ~/.hyperlex/chroma

# Cloud promote stays explicit (not on the hot ingest path)
$HLX vector-sync --from-path ~/.hyperlex/chroma --to cloud
$HLX vector-stats --cloud
```

Full map: [modules/vectordb.md](modules/vectordb.md) · [commands.md](commands.md).

## Week-one checklist

1. Install skill: `bash install.sh`
2. `$HLX doctor` green
3. **Burn-in (atomic offline runs):**
   ```bash
   bash examples/ops/burn-in.sh
   ```
   Or manually: `$HLX run "rizz" --route offline` (one atom per run)
4. Settle a handful of forecasts via `pending` → `settle`
5. `$HLX score-series --verify-chain` — first real Brier series
6. Optional: local Chroma backfill + `vector-sync --to cloud` (see above)
7. Only then: `--route live` or ELEVATED/CRITICAL tiers if advisory warrants

Atomic multi-term demos: [demos/atomic-terms.md](demos/atomic-terms.md)

## Command map

Full simplified map: [commands.md](commands.md) or `$HLX commands`.
