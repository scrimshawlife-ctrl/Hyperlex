# Demo: atomic multi-term seeds

## The short version

| You type | Engine does |
|----------|-------------|
| `pipeline "sigma rizz locked in"` | **Three** full result units: `sigma`, `rizz`, `locked in` |
| `pipeline "locked in"` | **One** unit (true multi-word phrase) |
| `pipeline "rizz"` | **One** unit |

The spaces in `"sigma rizz locked in"` are **input text**, not a single slang entry.  
Backfill packs already store those as separate rows — the pipeline matches that model.

!!! tip "Rule of thumb"
    If the pack has three terms, you should get **three** scenarios — never one blended seed.

## Why this shows up on Pages

Older demos used bags as if they were one seed. Snapshots are corrected:

| Snapshot | Atoms (separate) |
|----------|------------------|
| [backfill-phase5-rizz-2026](../archive/runs/backfill-phase5-rizz-2026/index.md) | sigma · rizz · locked in |
| [phase5-rizz-ai-demo](../archive/runs/phase5-rizz-ai-demo/index.md) | sigma · rizz · locked in |
| [backfill-phase5-ai-native-2026](../archive/runs/backfill-phase5-ai-native-2026/index.md) | agentic slop · skill issue |
| [backfill-phase5-sharp-2026](../archive/runs/backfill-phase5-sharp-2026/index.md) | sharp · steam · revenge |

On a multi-term card you should see **atoms** listed, plus a per-term table inside the snapshot.

## Live demos (offline)

```bash
export HERMES_SKILL_DIR="${HERMES_SKILL_DIR:-$HOME/.hermes/skills/hyperlex}"
export HLX="python3 $HERMES_SKILL_DIR/scripts/hyperlex.py"
export HYPERLEX_OFFLINE=1
```

### A — Automatic pipeline (preferred)

```bash
# Full backend results for each atom
$HLX pipeline "sigma rizz locked in" --route offline

# Packet fields that matter:
#   atoms: ["sigma","rizz","locked in"]
#   results: [ {query, receipt, forecasts, phase5}, ... ]
#   brier: null
```

Same automatic path: `run` and `ingest` (use `ingest --raw-only` only if you want the signal, no results).

### B — Preview split only

```bash
$HLX terms-split "sigma rizz locked in"
# → terms: ["sigma", "rizz", "locked in"]

$HLX terms-split "agentic slop skill issue"
# → ["agentic slop", "skill issue"]   # compound phrase kept

$HLX terms-split "locked in crash out"
# → ["locked in", "crash out"]
```

### C — Phase 5 research only

```bash
$HLX simulate --term "sigma rizz locked in" --domain ai
# → schema hyperlex.phase5_multi_term.v1

$HLX simulate --term rizz --domain ai
# → single atomic scenario
```

### D — Force blend (avoid)

```bash
$HLX simulate --term "sigma rizz locked in" --no-expand
# one scenario — only if you intentionally want a blended seed
```

## Expected shapes

### Pipeline multi-atom

```json
{
  "schema": "hyperlex.pipeline_result.v1",
  "atoms": ["sigma", "rizz", "locked in"],
  "n_atoms": 3,
  "results": [
    {"query": "sigma", "lineage_family": "…", "n_forecasts": 3, "brier": null},
    {"query": "rizz", "lineage_family": "…", "n_forecasts": 3, "brier": null},
    {"query": "locked in", "lineage_family": "…", "n_forecasts": 3, "brier": null}
  ],
  "brier": null
}
```

### Phase 5 multi-term

```json
{
  "schema": "hyperlex.phase5_multi_term.v1",
  "original_seed": "sigma rizz locked in",
  "terms": ["sigma", "rizz", "locked in"],
  "summaries": [
    {"seed_term": "sigma", "risk_tier": "…", "brier": null},
    {"seed_term": "rizz", "risk_tier": "…", "brier": null},
    {"seed_term": "locked in", "risk_tier": "…", "brier": null}
  ],
  "brier": null
}
```

## Repo fixtures

| File | Purpose |
|------|---------|
| [`examples/demos/atomic-terms-demo-bundle.json`](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/examples/demos/atomic-terms-demo-bundle.json) | Full demo matrix (tests load this) |
| [`examples/demos/terms-split-*.json`](https://github.com/scrimshawlife-ctrl/Hyperlex/tree/main/examples/demos) | Split outputs |
| [`examples/demos/phase5-multi-sigma-rizz-locked-in.json`](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/examples/demos/phase5-multi-sigma-rizz-locked-in.json) | Phase 5 multi summary |

## Related

- [Operator loop](../operator-loop.md) — day-to-day auto path  
- [Commands](../commands.md) — `pipeline` / `ingest` / `run`  
- [Phase 5](../phase5.md)  
- [Run history](../archive/index.md)  
