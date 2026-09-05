# Spec 002 — Hermes command surface (usability)

**Date:** 2026-09-04  
**Status:** SPECIFY / SHADOW  
**Depends on:** 000, 001, constitution v1.0.0  
**Problem:** Hyperlex already has too many top-level verbs. Mutation grammar must not add a second island (`mutation-predict` + `mutation-trace` + `python -m`).

## Intent
One noun. Few verbs. Pipeline is the default. Agents learn four daily commands and a research namespace. Mutation detect/predict live under that namespace. Dual-use wall stays in the verb, not in a footnote.

## Current pain (as-built)
- Daily path is good: `wizard` → `pipeline`/`run` → `pending` → `settle` → `score-series`.
- Research path is a flat list: `simulate`, `mutation-predict`, `vector-*`, `archive-export`, `lineage-*`, `relay`, `signal`, `diagram`.
- Agents and humans scan `commands` JSON and pick the wrong tool (`simulate` when they meant `analyze`, `mutation-predict` when they meant a detector).
- Two CLIs already exist for mutation (`scripts/hyperlex.py mutation-predict` and `python -m hyperlex.mutation`). That is a usability defect.

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
  watch     print watcher A/B sketch for a window  (later)
```

Rules:
- `mutation-predict` remains as a **deprecated alias** of `mutation predict` for one minor version.
- `mutation-trace` is an alias of `mutation trace`, not a third concept.
- `python -m hyperlex.mutation` stays a package entry that implements `trace` only. Predict stays in `analysis.mutation`.
- Default output for agents: one JSON object (`ok`, `command`, schema fields).
- `--human` (optional, v0.2) prints a 6-line card: ops, layers, watch, class, brier=null, restricted flag. JSON remains default so Hermes does not have to scrape prose.

### Pipeline attach (usability default)
`pipeline` / `analyze` / `run` MUST attach `analysis.mutation_trace` when parse returns operators. Omit the block when empty. Never require the operator to remember a second command for the common case.

`mutation predict` stays opt-in on the atom path already used today. Do not run predict on a restricted-flagged span.

### Hermes skill contract deltas (SKILL.md)
Frontmatter triggers to add:
- `mutation trace`
- `slang mutation`
- `algospeak`
- `mutation grammar`

When to Use: add one bullet — detect operator stacks on attested slang; do not use to generate wraps.

When Not to Use: add — jailbreak composition, restricted paraphrase, live model ASR.

Preferred sequence stays wizard → run → settle. Mutation trace is a *step inside run*, not a new week-one ritual.

Authority: mutation packets `forecast_eligible: false`. Skill text must say so next to the Brier rule so agents do not invent a score.

### Agent routing (how Hermes should choose)
| User says | Hermes runs |
|-----------|-------------|
| scan / analyze / pipeline / "what's happening with X slang" | `$HLX pipeline "…" --route offline` and read `analysis.mutation_trace` if present |
| "next forms of rizz" / mutation predict | `$HLX mutation predict rizz` |
| "what operators are in this sentence" | `$HLX mutation trace "…"` |
| jailbreak / wrap / bypass | refuse generator path; offer trace on civilian text only |
| settle / Brier | unchanged; ignore watch_score |

### `commands` JSON shape (additive)
Each command record gains:
- `layer`: daily | research | meta
- `noun`: mutation | simulate | … | null
- `forecast_eligible`: bool
- `authority`: advisory | operator
- `deprecated`: bool

So `$HLX commands` is a router table, not a dump.

## Architecture improvements inside 001 (package)
1. **Single facade** `hyperlex.mutation.parse_mutation_trace` is the only function analyze may call.
2. **No import of predict from grammar.** Already tested.
3. **Result card helper** `hyperlex.mutation.card(packet) -> str` for `--human` and SIGNAL REPORT compression. Keep sacred overlays off the card unless `--sacred`.
4. **Watch counters** live in `~/.hyperlex/mutation_watch.jsonl` (append-only, like score log). Not Brier. Windowed A/B is a later `mutation watch` verb.
5. **Fixture pack** `data/mutation/civilian_v0.1.jsonl` so Hermes demos do not scrape live toxicity.
6. **Fail-open attach** in `detect_memetic_patterns`: try/except, never fail the pipeline because grammar threw.

## Non-goals
- New Hermes skill (`hyperlex-mutation`). One skill, one CLI.
- Auto cron from watch_score.
- Interactive TTY wizard step for mutation in week-one.
- Merging predict and trace into one verb with a flag. Flags hide polarity. Verbs show it.

## Success
- An agent that only read SKILL.md + `commands` can pick `pipeline` vs `mutation trace` vs `mutation predict` without this spec.
- Week-one path length unchanged.
- Dual-use polarity is visible in the verb name.
