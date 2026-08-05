# Demo: atomic multi-term seeds

Independent slang items must be **considered separately**. Multi-word phrases that are one item (`locked in`, `skill issue`, `agentic slop`) stay together.

!!! tip "Rule of thumb"
    If backfill stores three pack rows, Phase 5 should produce **three scenarios** — not one blended seed.

## Why this matters

| Wrong | Right |
|-------|--------|
| One Phase 5 run for `"sigma rizz locked in"` | Three runs: `sigma` · `rizz` · `locked in` |
| One lineage score density-stacking all hits | `per_term[]` lineage; primary = best single atom |
| Scan queries that bag unrelated atoms | Atomic pack in `examples/cron/scan-queries.json` |

## Live demos (run offline)

```bash
export HERMES_SKILL_DIR="${HERMES_SKILL_DIR:-$HOME/.hermes/skills/hyperlex}"
export HLX="python3 $HERMES_SKILL_DIR/scripts/hyperlex.py"
export HYPERLEX_OFFLINE=1
```

### Demo A — brainrot bag

```bash
$HLX terms-split "sigma rizz locked in"
# → terms: ["sigma", "rizz", "locked in"]

$HLX simulate --term "sigma rizz locked in" --domain ai --no-phylogeny
# → schema hyperlex.phase5_multi_term.v1
# → one summary per atom

# Prefer day-to-day atomic runs:
$HLX run "sigma" --route offline
$HLX run "rizz" --route offline
$HLX run "locked in" --route offline
```

### Demo B — AI-native compound + phrase

```bash
$HLX terms-split "agentic slop skill issue"
# → ["agentic slop", "skill issue"]   # compound phrase kept

$HLX simulate --term "agentic slop skill issue" --domain ai --no-phylogeny
```

### Demo C — betting atoms

```bash
$HLX terms-split "sharp steam revenge"
# → ["sharp", "steam", "revenge"]

$HLX simulate --term "sharp steam revenge" --domain markets --no-phylogeny
```

### Demo D — discipline pair

```bash
$HLX terms-split "locked in crash out"
# → ["locked in", "crash out"]

$HLX analyze "locked in crash out" --route offline
# analysis.seed_terms.terms · analysis.per_term · analysis.primary_term
```

### Force blend (opt-in only)

```bash
$HLX simulate --term "sigma rizz locked in" --no-expand --domain ai
# single hyperlex.phase5_scenario.v1 — use only if you mean it
```

## Expected shapes

### `terms-split`

```json
{
  "schema": "hyperlex.seed_terms.v1",
  "original": "sigma rizz locked in",
  "terms": ["sigma", "rizz", "locked in"],
  "multi_term": true,
  "method": "lexicon_longest_match"
}
```

### Phase 5 multi-term

```json
{
  "schema": "hyperlex.phase5_multi_term.v1",
  "original_seed": "sigma rizz locked in",
  "terms": ["sigma", "rizz", "locked in"],
  "multi_term": true,
  "summaries": [
    {"seed_term": "sigma", "risk_tier": "…", "brier": null},
    {"seed_term": "rizz", "risk_tier": "…", "brier": null},
    {"seed_term": "locked in", "risk_tier": "…", "brier": null}
  ],
  "brier": null,
  "provenance": "SPECULATIVE"
}
```

### Analyze

| Field | Meaning |
|-------|---------|
| `analysis.seed_terms` | Split packet |
| `analysis.per_term[]` | Lineage per atom |
| `analysis.primary_term` | Best single-atom pick |
| `analysis.lineage` | Primary lineage (`multi_term_mode: true` when bag) |
| `analysis.lineage_bag` | Optional density-stacked bag (not primary) |

## Fixture files (repo)

Checked into `examples/demos/`:

| File | Purpose |
|------|---------|
| [terms-split-sigma-rizz-locked-in.json](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/examples/demos/terms-split-sigma-rizz-locked-in.json) | Split demo A |
| [terms-split-agentic-slop-skill-issue.json](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/examples/demos/terms-split-agentic-slop-skill-issue.json) | Split demo B |
| [terms-split-locked-in-crash-out.json](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/examples/demos/terms-split-locked-in-crash-out.json) | Split demo D |
| [phase5-multi-sigma-rizz-locked-in.json](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/examples/demos/phase5-multi-sigma-rizz-locked-in.json) | Phase 5 multi summary |
| [atomic-terms-demo-bundle.json](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/examples/demos/atomic-terms-demo-bundle.json) | All cases (tests load this) |

## Pages archive demos

Multi-term Phase 5 snapshots (already expanded):

- [backfill-phase5-rizz-2026](../archive/runs/backfill-phase5-rizz-2026/index.md) — sigma · rizz · locked in  
- [phase5-rizz-ai-demo](../archive/runs/phase5-rizz-ai-demo/index.md) — same atoms  
- [backfill-phase5-ai-native-2026](../archive/runs/backfill-phase5-ai-native-2026/index.md) — agentic slop · skill issue  
- [backfill-phase5-sharp-2026](../archive/runs/backfill-phase5-sharp-2026/index.md) — sharp · steam · revenge  

## Related

- [Operator loop](../operator-loop.md)  
- [Phase 5](../phase5.md)  
- [Commands](../commands.md)  
- [Backfill packs](https://github.com/scrimshawlife-ctrl/Hyperlex/tree/main/data/backfill/2026)  
