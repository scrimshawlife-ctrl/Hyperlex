# Spec 002 — Hermes command surface (usability)

**Date:** 2026-09-04  
**Status:** SPECIFY locked / implement SHADOW  
**Depends on:** 000, 001, constitution v1.0.0  
**Problem:** Hyperlex already has too many top-level verbs. Mutation grammar must not add a second island (`mutation-predict` + `mutation-trace` + `python -m`).

## Intent
One noun. Few verbs. Pipeline is the default. Agents learn four daily commands and a research namespace. Mutation detect/predict live under that namespace. Dual-use wall stays in the verb, not in a footnote.

## Command architecture (normative)

### Layers
1. **Daily** — `wizard`, `pipeline`/`run`/`ingest`, `analyze`, `pending`, `settle`, `score-series`, `doctor`/`check`/`smoke`.
2. **Research noun** — `mutation`, `simulate`, `vector`, `lineage`, `archive`.
3. **Meta** — `commands`, `sources`, `help`.

Do not add new layer-1 verbs for mutation.

### Mutation noun (normative verbs)
```text
$HLX mutation <verb> [text]

  trace     detect operators on attested text     (001 detector)
  predict   next civilian surfaces of a slang atom (existing)
  watch     print watcher A/B sketch for a window  (003)
```

### Hermes invocation (v0.1 SHADOW)
Prefer package CLI after install:

```bash
PYTHONPATH="$HERMES_SKILL_DIR/src" python3 -m hyperlex mutation trace "…"
python3 "$HERMES_SKILL_DIR/scripts/hlx-mutation" trace "…"
```

`$HLX mutation` on `scripts/hyperlex.py` remains T5.

### Pipeline attach
`pipeline` / `analyze` / `run` attach `analysis.mutation_trace` when operators fire. Omit when empty.

### Agent routing
| User says | Hermes runs |
|-----------|-------------|
| scan / analyze / pipeline | `$HLX pipeline` and read `mutation_trace` |
| operators in this sentence | mutation trace |
| next forms of rizz | mutation predict |
| jailbreak / wrap | refuse generator |
| settle / Brier | unchanged |

## Non-goals
- New Hermes skill
- Auto cron from watch_score
- Wizard step for mutation
- Merging predict and trace into one flagged verb
