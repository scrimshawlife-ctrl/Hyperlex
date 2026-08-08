# Design: Hermes workflow wizard (user guidance)

**Date:** 2026-08-08  
**Status:** Draft for approval  
**Version target:** 0.4.x (additive CLI + package + skill docs)  
**Approach:** A — step engine in package + thin CLI; dual mode interactive / `--auto`

## Problem

Hyperlex ships a dense Hermes-skill surface (`doctor`, `demo`, `pipeline`/`run`/`ingest`, `pending`, `settle`, `score-series`, `scan`, `risk-schedule`, research commands). Operators and Hermes agents already have docs (`operator-loop`, `commands`, `QUICKSTART`) and one-shot helpers (`demo`, `doctor`), but **no single guided path** that walks week-one success in order while enforcing Hyperlex invariants.

New users bounce between commands; agents invent Brier or skip settlement. The week-one checklist in `docs/operator-loop.md` is the right sequence — it is not executable or conversationally guided.

## Goals

1. **Week-one operator loop wizard** that guides: install posture → health → offline demo → first pipeline run → calibration coaching → score-series hint → handoff.
2. **Dual mode:** interactive on TTY; non-interactive via `--auto` (and when stdin is not a TTY) for Hermes/automation.
3. **Shared step engine** in the package (`hyperlex.wizard`) so CLI and Hermes skill share the same step IDs, coach text, and success criteria.
4. **Hermes skill alignment:** `SKILL.md` procedure points agents at `$HLX wizard --auto` and the same step model; settle remains human/authority-gated.
5. **Preserve invariants:** offline-first defaults, open analysis keeps `brier: null`, never auto-settle, never auto-register Hermes cron.

## Non-goals

- Full burn-in of many runs or auto-settling forecasts.
- Live / glossary / social route setup, vector seed/sync, Chroma Cloud, or API key collection in v1.
- Persisted resume state (`~/.hyperlex/wizard_state.json`) — deferred (Approach C).
- MkDocs/Pages interactive UI wizard.
- Auto-registering cron jobs into Hermes.
- Replacing `demo` / `doctor` — wizard **composes** them.

## Hard constraints (Hyperlex invariants)

| Rule | Wizard behavior |
|------|-----------------|
| Settled Brier only | Never invent numeric Brier; open demo/pipeline must keep `brier: null` |
| Operator settlement | Step `calibration_coach` explains settle; **never** calls settle without explicit user authority |
| Offline first | Default route `offline`; `--auto` forces offline-safe path |
| Fail-open / fail-closed | Doctor failure is degraded (continue unless `--strict`); integrity failures (non-null open brier) fail the wizard |
| Advisory cron only | Handoff mentions `risk-schedule` as paste-into-Hermes; never registers jobs |
| Atomic terms | First pipeline may use multi-term sample that expands to atoms (existing pipeline behavior) |

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Hermes agent (SKILL.md procedure)                          │
│    preferred: $HLX wizard --auto                            │
│    then: coach pending → settle (authority) → score-series  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  scripts/hyperlex.py  →  cmd_wizard                         │
│    flags: --auto --query --skip-doctor --strict --out       │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  hyperlex.wizard (package)                                  │
│    steps registry · runner · result schema                  │
│    reuses: doctor checks, run_pipeline / demo path,         │
│            pending index, score-series (read-only unless    │
│            settlements already exist)                       │
└─────────────────────────────────────────────────────────────┘
```

### Module layout

```text
src/hyperlex/wizard/
  __init__.py          # public: run_wizard, WIZARD_STEPS, schema const
  steps.py             # ordered step definitions (id, title, run, coach)
  runner.py            # execute steps, mode resolution, aggregate result
  text.py              # human-facing coach / handoff strings (optional split)
```

CLI remains thin: import `run_wizard`, emit JSON via existing `_emit` pattern.

### Modes

| Mode | When | Behavior |
|------|------|----------|
| `interactive` | TTY and not `--auto` | Print step titles; optional prompts (query override, continue/skip where allowed); defaults on empty enter |
| `auto` | `--auto` **or** non-TTY stdin | No prompts; fixed offline path; print structured result + next actions |

Silence / empty answers in interactive mode continue with defaults (Hermes onboarding policy style).

## Step model

Schema: `hyperlex.wizard.v1`

Ordered steps (stable IDs — Hermes and docs refer to these):

| # | `id` | Action | Auto | Notes |
|---|------|--------|------|-------|
| 1 | `env_intro` | Print skill root, suggested `HLX`, offline-first posture, data dirs under `~/.hyperlex/` | yes | Never requires network |
| 2 | `doctor` | Run existing doctor checks (or invoke shared health helpers) | yes | Soft-fail: continue with `degraded=true` unless `--strict` |
| 3 | `demo` | Offline demo path (compose `cmd_demo` / `run_pipeline` offline); assert open `brier is null` | yes | Default query `rizz` |
| 4 | `first_pipeline` | `run_pipeline(query, route=offline, receipt+forecasts+append_log)` | yes | Query from `--query` or interactive default `rizz` / user input |
| 5 | `calibration_coach` | List open forecasts via pending index; print settle recipe | yes | **No settle calls** |
| 6 | `score_series_hint` | If any settlements exist → run score-series (read/recompute); else print “settle first” | yes | Does not invent Brier |
| 7 | `handoff` | `risk-schedule` tip, docs links (`operator-loop`, `commands`, `settled-brier`), `$HLX commands` | yes | Advisory only |

Each step result:

```json
{
  "id": "demo",
  "ok": true,
  "skipped": false,
  "degraded": false,
  "summary": "offline demo ok; lineage_family=brainrot-aura; brier=null",
  "coach": ["Next: settle open forecasts with operator authority."],
  "artifacts": {"log_path": "…", "receipt": "…"},
  "error": null
}
```

Aggregate wizard result:

```json
{
  "schema": "hyperlex.wizard.v1",
  "version": "<pkg version>",
  "ok": true,
  "mode": "auto",
  "query": "rizz",
  "route": "offline",
  "brier": null,
  "steps": [ /* per-step */ ],
  "next": [
    "python3 …/scripts/hyperlex.py pending",
    "python3 …/scripts/hyperlex.py settle --forecast-id <id> --decision TRUE",
    "python3 …/scripts/hyperlex.py score-series --mean-shift --verify-chain"
  ],
  "note": "Week-one guided path. Never invent Brier. Never auto-settle."
}
```

## CLI surface

```bash
$HLX wizard
$HLX wizard --auto
$HLX wizard --auto --query "locked in"
$HLX wizard --skip-doctor
$HLX wizard --strict          # doctor failure aborts
$HLX wizard --out /tmp/hlx-wizard.json
```

Registration:

- `subparsers.add_parser("wizard", …)` in `scripts/hyperlex.py`
- `commands` map: add under `daily_ops` (first entry or after `demo`)
- `docs/commands.md` table row
- `docs/operator-loop.md` week-one checklist: step 0 = wizard
- `QUICKSTART.md` and `docs/start/quickstart.md` mention `$HLX wizard --auto`
- `SKILL.md`: **Guided wizard** section + preferred sequence update
- `docs/hermes-skill.md`: one paragraph + command example

Optional alias: none required (`guide` deferred).

## Hermes skill procedure

When user says “get started with Hyperlex”, “Hyperlex wizard”, “guide me through Hyperlex”, or first-use after install:

1. Ensure skill install path; set `HERMES_SKILL_DIR` / `HLX` if missing.
2. Run `$HLX wizard --auto` (or with user-supplied query).
3. Present step summaries; highlight open forecasts from `calibration_coach`.
4. **Settlement:** ask for operator decision; only then run `settle` with authority.
5. Run `score-series --mean-shift --verify-chain` after at least one settlement.
6. Offer optional `risk-schedule --tier MODERATE` as advisory paste — do not auto-register.

Triggers to add (examples): `hyperlex wizard`, `get started with hyperlex`, `hyperlex onboarding`.

## Error handling

| Condition | Behavior |
|-----------|----------|
| Import / package broken | Fail step, `ok: false`, stop |
| Doctor checks fail | Soft continue (`degraded`); `--strict` → stop |
| Demo or first_pipeline fails | Stop; remediation coach (install, offline, PYTHONPATH) |
| Open analysis has non-null brier | Fail integrity; stop |
| No open forecasts after pipeline | Coach that forecasts may be empty for some queries; suggest another term; still `ok` if pipeline succeeded |
| Non-TTY without `--auto` | Treat as `auto` (no hang on prompts) |
| Settle never invoked by wizard | Guaranteed by design / tests |

## Testing

| Test | Asserts |
|------|---------|
| `test_wizard_step_order` | Stable step IDs and order |
| `test_wizard_auto_offline` | `run_wizard(mode="auto")` succeeds offline; aggregate `brier is null` |
| `test_wizard_no_settle_side_effect` | Score log settlement count unchanged across wizard |
| `test_wizard_strict_doctor` | Mocked doctor failure + strict → non-zero / `ok: false` |
| `test_wizard_schema` | Result has `schema == hyperlex.wizard.v1` and required keys |
| CLI smoke (optional) | `python3 scripts/hyperlex.py wizard --auto` exit 0 in CI offline |

Reuse existing offline / mock patterns from `test_demo_offline.py` and doctor tests.

## Docs & packaging touch list

- `src/hyperlex/wizard/*` (new)
- `src/hyperlex/__init__.py` — export `run_wizard` only if API_V1 discipline wants it; otherwise keep internal and CLI-import path stable
- `scripts/hyperlex.py` — `cmd_wizard` + parser
- `tests/test_wizard.py` (new)
- `SKILL.md`, `docs/hermes-skill.md`, `docs/operator-loop.md`, `docs/commands.md`, `QUICKSTART.md`, `docs/start/quickstart.md`
- `CHANGELOG.md` / `STATUS.md` when implementing
- `commands` JSON map inside CLI

## Success criteria

1. `$HLX wizard --auto` completes week-one offline path without network or API keys.
2. Structured output is machine-readable and step-stable for Hermes.
3. No settlement writes; open `brier` remains null.
4. Interactive mode works on TTY with defaults-on-enter.
5. Docs and SKILL.md tell the same story as the step engine.
6. Tests cover order, auto path, no-settle, schema.

## Implementation sketch (not a plan)

1. Add `hyperlex.wizard` step registry + runner.
2. Wire CLI `wizard` and command map.
3. Tests for auto offline path and invariants.
4. Update SKILL.md + operator docs.
5. Manual: install skill, run wizard --auto, settle one forecast by hand, score-series.

## Open decisions (resolved in brainstorming)

| Decision | Choice |
|----------|--------|
| Surface | CLI + Hermes skill |
| Depth | Week-one operator loop |
| Non-TTY | Dual mode interactive + `--auto` |
| Shape | Package step engine + thin CLI |
| Persist progress | Deferred |

## Out of scope follow-ups

- Resume / skip completed steps via state file
- Live-route branch of wizard
- Vector seed coach
- `guide` alias / Pages widget
- Auto-settle with explicit `--i-authorize-settle` (likely never; keep human)
