---
name: hyperlex
description: >
  Use when the user wants memetic emergence analysis, slang detection,
  hyperstition / virality scoring, slang lineage matching, forecast extraction,
  operator settlement, Brier calibration on cultural signals, or slang
  mutation-operator detection on attested text. Triggers include slang,
  memetics, hyperstition, virality, lineage, mutation trace, algospeak,
  Brier, settle forecasts, score-series, betting slang, crypto-degen slang,
  ai-native slang, brainrot, and receipt-backed cultural signal scans.
  Not for general web research (use agent-reach), product audits (neon-genie),
  cinematic work (kubrick), or jailbreak / wrap composition.
when_to_use: >
  Invoke for slang detection, memetic emergence, lineage matching,
  hyperstition or virality scoring, forecast settlement, or mutation
  traces. Prefer the Hyperlex CLI over inventing scores.
allowed-tools:
  - Bash
  - Read
  - Grep
version: 0.4.2
author: Applied Alchemy Labs / Hermes
license: LicenseRef-Zero-State-Proprietary-1.0
platforms: [linux, macos]
dependencies: []
metadata:
  hermes:
    tags:
      - Memetics
      - Slang
      - Hyperstition
      - Virality
      - Lineage
      - Calibration
      - Brier
      - Receipts
      - Forecasting
      - Mutation
    category: analysis
    related_skills: []
  claude:
    hosts: [claude-code]
    personal_skill: ~/.claude/skills/hyperlex
    plugin_dir: ~/.claude/plugins/hyperlex
    plugin_manifest: .claude-plugin/plugin.json
  openclaw:
    requires:
      bins: [python3]
    os: [darwin, linux]
    emoji: "🌀"
triggers:
  - hyperlex
  - memetic
  - memetics
  - slang
  - slang lineage
  - hyperstition
  - virality
  - neologism
  - betting slang
  - sharp money
  - brainrot
  - brier
  - settle forecast
  - score series
  - cultural signal
  - memetic receipt
  - hyperlex wizard
  - get started with hyperlex
  - hyperlex onboarding
  - mutation trace
  - mutation grammar
  - algospeak
  - slang mutation
---

# Hyperlex

Standalone **Hermes skill** for memetic emergence analysis.

Hermes loads this directory and uses `SKILL.md` as the behavior contract.
The runtime is the bundled Python package under `src/hyperlex/` plus the CLI
at `scripts/hyperlex.py`. No Abraxas import, no required network for baseline
(`mock`) mode.

Resolve paths from the installed skill root. Set:

```bash
export HERMES_SKILL_DIR="${HERMES_SKILL_DIR:-$HOME/.hermes/skills/hyperlex}"
```

## When to Use

- Detect slang / neologisms and score virality, memetics, hyperstition
- Match slang into historical **lineage families** with transparent confidence
- Detect slang **mutation operator stacks** on attested text (`mutation trace`)
- Next civilian surfaces of a slang atom (`mutation predict`) — SPECULATIVE, not Brier
- **Backfill** YTD slang packs and **backpropagate** lineage onto historical receipts (non-mutating)
- **Phase 5 simulate** cultural transmission, multi-agent memetics, hyperstition risk, phylogeny scaffold
- **Risk-schedule** advisory LIVE_EMERGENCE_SCAN cadence from risk tiers (never auto-registers cron)
- Emit integrity-hashed **receipts** for auditable runs
- Extract **forecasts** from analysis (probabilities only — no fake Brier)
- **Settle** forecasts as an operator and recompute Brier series from the score log
- Scan betting-sharp, crypto-degen, ai-native, brainrot, kinship, political-status families

## When Not to Use

- General multi-platform web research → agent-reach
- Product / opportunity intelligence → neon-genie
- Cinematic continuity / storyboards → kubrick
- Symbolic code architecture mapping → orchestra
- Jailbreak / wrap composition / model ASR boards — detector only; no generator path

## Prerequisites

- Python 3.10+
- `python3` on PATH
- Optional: `requests`, `jsonschema`, `crawl4ai` for richer ingest / validation
- Optional: network for non-`mock` sources

## Install

```bash
bash install.sh --dry-run
bash install.sh
# installs to ~/.hermes/skills/hyperlex by default
python3 "$HOME/.hermes/skills/hyperlex/scripts/hyperlex.py" check
python3 "$HOME/.hermes/skills/hyperlex/scripts/hyperlex.py" smoke
```

Claude Code personal skill (Hermes install still runs; this flag is additive):

```bash
bash install.sh --claude --dry-run
bash install.sh --claude
# ~/.claude/skills/hyperlex  + sibling slash helpers
# optional plugin tree: bash install.sh --claude-plugin
```

## Claude Code

Claude is an additional host. Hermes remains the primary skill surface.
Prefer the Bash CLI. Do not invent scores. Do not auto-settle.

```bash
export HYPERLEX_SKILL_DIR="${HYPERLEX_SKILL_DIR:-${HERMES_SKILL_DIR:-$HOME/.claude/skills/hyperlex}}"
export HERMES_SKILL_DIR="${HERMES_SKILL_DIR:-$HYPERLEX_SKILL_DIR}"
export HLX="${HLX:-python3 $HYPERLEX_SKILL_DIR/scripts/hyperlex.py}"
# wrapper: bash scripts/claude_hlx.sh
# after pip: hyperlex
```

When to call:

| Need | Command |
|------|---------|
| First success | `$HLX demo` |
| Week-one path | `$HLX wizard --auto` |
| Analyze + receipt | `$HLX pipeline "<term>" --route offline` |
| Multi-query scan | `$HLX scan --query "<term>" --route offline --receipt --forecasts` |
| Open forecasts | `$HLX pending` |
| Close a forecast | `$HLX settle --forecast-id <id> --decision TRUE` after the human chooses |

Slash helpers (project `.claude/skills/` or plugin `commands/`): `/hyperlex`,
`/hyperlex-demo`, `/hyperlex-wizard`, `/hyperlex-scan`, `/hyperlex-analyze`,
`/hyperlex-pending`, `/hyperlex-settle`.

Fail-closed: never invent Brier; never auto-settle; repeat OBSERVED / INFERRED /
SPECULATIVE. Docs: `docs/claude-skill.md`, `CLAUDE.md` (project only — plugin
context does not load `CLAUDE.md`).

## Commands (prefer simplified path)

```bash
HLX="python3 $HERMES_SKILL_DIR/scripts/hyperlex.py"

$HLX wizard --auto                 # week-one guided path (offline)
$HLX wizard                        # interactive (TTY)
$HLX commands                          # full simplified map (JSON)
$HLX sources                           # sources + routes
# AUTO backend — ingest → full results (receipt, forecasts, phase5 risk)
$HLX pipeline "rizz" --route offline
$HLX ingest "locked in"                # same as pipeline (use --raw-only for signal only)
$HLX pipeline "sigma rizz locked in"   # expands to atoms automatically
$HLX pending                           # open forecasts
$HLX settle --forecast-id <id> --decision TRUE --authority-ref <ref> --settle-token "$HYPERLEX_SETTLE_TOKEN"
$HLX score-series --mean-shift --verify-chain
$HLX scan --route offline --receipt --forecasts --append-log
$HLX risk-schedule --tier MODERATE --schedule-out /tmp/hlx-cron
$HLX doctor && $HLX smoke
```

**Ingest routing:** prefer `--route offline|live|glossary|social` over raw `--source`.
Aliases: `real`→glossary, `x`→x_search, `firecrawl`→crawl4ai. Offline env: `HYPERLEX_OFFLINE=1`.

Mutation (package CLI; prefer this over inventing a second skill):

```bash
PYTHONPATH="$HERMES_SKILL_DIR/src" python3 -m hyperlex mutation trace "it's giving mid rizz"
PYTHONPATH="$HERMES_SKILL_DIR/src" python3 -m hyperlex mutation trace "rzz" --human
PYTHONPATH="$HERMES_SKILL_DIR/src" python3 -m hyperlex mutation watch
PYTHONPATH="$HERMES_SKILL_DIR/src" python3 -m hyperlex mutation predict rizz
```

`pipeline` / `analyze` attach `analysis.mutation_trace` when operators fire.
`trace --human` prints a civilian advisory card. `trace --watch-jsonl` appends instrumentation (not probabilities; never auto-fires tools).
Do not add a wizard step. Do not add `wrap` / `compose` / `asr` verbs.
Lane is SHADOW / advisory.

Research / advanced: `simulate`, `vector-*`, `archive-export`,
`lineage-backfill`, `lineage-backprop`, `relay`, `signal`, `diagram`, `ledger-*`.

Docs: `docs/operator-loop.md`, `docs/commands.md`.

## Guided wizard

When the user is new to Hyperlex, asks to get started, or wants a guided
operator path:

1. Ensure skill install (`bash install.sh` if missing).
2. Run `$HLX wizard --auto` (or `$HLX wizard --auto --query "<term>"`).
3. Summarize steps: env → doctor → demo → first pipeline → calibration coach.
4. **Never invent Brier.** Open analysis keeps `brier: null`.
5. Show open forecasts from the wizard output / `$HLX pending`.
6. **Settlement requires operator authority** — ask for TRUE|FALSE|VOID, then:
   `$HLX settle --forecast-id <id> --decision …`
7. `$HLX score-series --mean-shift --verify-chain`
8. Optional advisory only: `$HLX risk-schedule --tier MODERATE --schedule-out /tmp/hlx-cron`
   (never auto-register Hermes cron).

Step IDs (stable): `env_intro`, `doctor`, `demo`, `first_pipeline`,
`calibration_coach`, `score_series_hint`, `handoff`.

### Operator calibration path

```text
run "<query>" --route offline
  → pending
  → settle --forecast-id … --decision TRUE|FALSE
  → score-series [--mean-shift] [--verify-chain]
```

- Score log default: `~/.hyperlex/score_log.jsonl`
- Override: `HYPERLEX_SCORE_LOG`, `--log`, or `--repo-log` → `out/calibration/score_log.jsonl`
- **Never** emit numeric Brier without settlement. Empty series → `NOT_COMPUTABLE`.

## Preferred sequence

1. **`wizard --auto`** then `commands` / `run` — week-one guided path, then map or one-shot.
2. **`run --route offline`** — one-shot analyze + receipt + forecasts + score log.
3. **`pending` → `settle` → `score-series`** — Brier only after operator settlement.
4. **Cron** — `risk-schedule` (advisory) + `scan --route offline` for multi-query.
5. **Live ingest** — only when network allowed: `--route live` (or glossary/social).
6. **Label claims** — `OBSERVED` / `INFERRED` / `SPECULATIVE`; fail closed on missing outcomes.
7. **Research** — `mutation trace` / `mutation predict` / `simulate` / archive / vector are optional and SPECULATIVE. Watch scores are not Brier.

## Public API (package)

```python
from hyperlex import (
    ingest_signal, fetch_ingest, detect_memetic_patterns,
    match_lineage, emit_receipt, extract_forecasts,
    settle_and_log, recompute_series, score_pair, score_series,
    NOT_COMPUTABLE,
)
from hyperlex.mutation import parse_mutation_trace

result = detect_memetic_patterns(query="rizz", ingest_source="mock")
trace = parse_mutation_trace("it's giving mid rizz")
forecasts = extract_forecasts(result)
# later, after operator review:
# settle_and_log(forecast, outcome_value=1.0, settlement_decision="TRUE")
# recompute_series()
```

Ensure `src/` is on `PYTHONPATH` when importing outside the CLI
(CLI inserts `src/` automatically).

## Authority boundaries

Hyperlex **may**:

- ingest and analyze signals
- match lineages with transparent score breakdowns
- detect mutation operator stacks on attested text
- extract forecasts and write receipts / score-log events
- compute Brier only from settled pairs
- export Abraxas-compatible ledger shapes (no Abraxas import)

Hyperlex **may not**:

- invent numeric Brier on open analysis (`provenance.brier` stays `null`)
- treat `watch_score` as Brier or as a tool-fire threshold
- auto-settle without authority marker
- promote speculative hyperstition stages as hard truth
- rewrite historical receipt integrity during lineage backprop (report only)
- invent Brier from Phase 5 simulation (always `brier: null`, SPECULATIVE)
- mutate Abraxas or other systems (export is optional and offline)
- generate restricted wraps, ASR boards, or call predict on restricted spans

## Pitfalls

- `scripts/hyperlex.py` must not shadow the package: always run via the skill path so `src/` is first on `sys.path`.
- Non-`mock` sources need network and may degrade gracefully — check ingest metadata.
- Lineage confidence is **INFERRED**; do not treat it as observed ground truth.
- Mean-shift from `score-series --mean-shift` is **advisory** for future forecasts only.
- Score log is append-only; series is recomputed from the log, not stored as sole truth.
- Mutation predict is civilian next-forms only. Detector and generator stay separate modules.

## Verification

```bash
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" check
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" doctor
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" ledger-stats
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" signal --input <result.json>
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" feedback --signal-key hyperstition.stage
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" diagram --from-golden --out-dir out/diagrams
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" scan --config "$HERMES_SKILL_DIR/examples/cron/scan-queries.json" --source mock --receipt --forecasts
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" smoke
PYTHONPATH="$HERMES_SKILL_DIR/src" python3 -m hyperlex mutation trace "it's giving mid rizz"
```

Successful packaging:

- `~/.hermes/skills/hyperlex/SKILL.md` exists
- optional Claude: `~/.claude/skills/hyperlex/SKILL.md` after `install.sh --claude`
- `check` returns `"ok": true`
- `smoke` writes a receipt under `out/smoke/`
- Open analysis has `"brier": null`
- Mutation trace packets have `"forecast_eligible": false`
- `doctor` reports `CLAUDE_OK` or `CLAUDE_MISSING` (missing does not fail the skill)

## Design references

- `DESIGN.md` — principles (incl. 11 lineage, 12 Brier requires settlement)
- `docs/brier-calibration.md` — forecast → settlement → score
- `docs/slang-lineages.md` — family methodology
- `docs/phase5.md` / `docs/modules/simulation.md` — Phase 5 research simulation
- `specs/001-mutation-grammar/` — detector grammar + dual-use gate
- `specs/003-mutation-detect-v02/` — GAME_ENCODE / CODE_SWITCH / PHONETIC_WARP + watch jsonl + `--human` (SHADOW)
- `schemas/` — ingest, result, receipt, forecast, settlement, brier_series, lineage, mutation_trace
- `examples/slang-families/` — Mermaid + HTML family diagrams
- `data/backfill/2026/` — YTD slang packs
- `references/hermes-runtime-contract.md` — path / authority policy
- `references/claude-runtime-contract.md` — Claude Code paths / env / CLI
- `references/source-and-upgrades.md` — install identity, two-rename limits, lock recovery

## Security

Local stdlib-first CLI. Baseline (`mock`) needs no network. Real ingest may call public web APIs. Score log and receipts are local files under `~/.hyperlex/` or skill `out/`.
Mutation packets are untrusted structured output (hosts must not execute fields).
Source, profile, and migration rules: `references/source-and-upgrades.md`.
