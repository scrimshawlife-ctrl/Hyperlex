<p align="center">
  <img src="assets/hyperlex-imagine-hero.jpg" alt="Hyperlex — memetic emergence" width="420">
</p>

<h1 align="center">Hyperlex</h1>

<p align="center">
  <strong>Catch language while it’s still becoming culture.</strong><br>
  <em>Hermes skill · memetic emergence engine · settled forecasts only</em>
</p>

<p align="center">
  <a href="https://github.com/scrimshawlife-ctrl/Hyperlex/actions/workflows/hermes-evals.yml"><img src="https://img.shields.io/github/actions/workflow/status/scrimshawlife-ctrl/Hyperlex/hermes-evals.yml?branch=main&label=skill%20ci&logo=github" alt="Skill CI"></a>
  <a href="https://github.com/scrimshawlife-ctrl/Hyperlex/actions/workflows/docs.yml"><img src="https://img.shields.io/github/actions/workflow/status/scrimshawlife-ctrl/Hyperlex/docs.yml?branch=main&label=docs&logo=github" alt="Docs CI"></a>
  <a href="https://scrimshawlife-ctrl.github.io/Hyperlex/"><img src="https://img.shields.io/badge/docs-GitHub%20Pages-0d9488?logo=markdown" alt="Docs"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <a href="./VERSION"><img src="https://img.shields.io/badge/version-0.4.0-informational" alt="Version 0.4.0"></a>
  <img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-3776AB?logo=python&logoColor=white" alt="Python 3.10, 3.11, and 3.12">
  <img src="https://img.shields.io/badge/hermes-skill-7c3aed" alt="Hermes skill">
  <img src="https://img.shields.io/badge/claude%20code-skill%20%2B%20plugin-d97706" alt="Claude Code">
  <img src="https://img.shields.io/badge/offline--first-mock%20route-22c55e" alt="Offline-first">
  <img src="https://img.shields.io/badge/Brier-settlement%20required-f59e0b" alt="Brier requires settlement">
</p>

<p align="center">
  <a href="https://scrimshawlife-ctrl.github.io/Hyperlex/">Docs home</a> ·
  <a href="https://scrimshawlife-ctrl.github.io/Hyperlex/start/quickstart/">Quickstart</a> ·
  <a href="https://scrimshawlife-ctrl.github.io/Hyperlex/start/see-it-work/">See it work</a> ·
  <a href="https://scrimshawlife-ctrl.github.io/Hyperlex/commands/">Commands</a> ·
  <a href="https://scrimshawlife-ctrl.github.io/Hyperlex/specs/">Specs</a> ·
  <a href="./STATUS.md">Status</a> ·
  <a href="./CONTRIBUTING.md">Contribute</a>
</p>

<p align="center">
  <sub>First success, no API keys: <code>python3 scripts/hyperlex.py demo</code></sub>
</p>

---

## What it is

Hyperlex is a **cultural radar for slang**. It watches phrases as they leak out of chats, betting desks, crypto timelines, and AI-native meme stacks, then answers practical questions:

- What just showed up?
- Which of the **8 lineage families** does it belong to?
- How hard is it spreading?
- Is it noise, or is it starting to make itself real (hyperstition)?
- If you forecast, can you **score yourself later** — only after the world answers?

It runs as a **Hermes skill** (Claude Code is an additional host). Offline-friendly by default. Receipt-backed when you care. One stubborn rule: **no fake accuracy**. Brier scores appear only after a human settles an outcome.

Cool without the con: less “AI vibe report,” more **flight recorder for memetic weather**.

---

## Quickstart

From this repo — no Hermes host, no API keys:

```bash
python3 scripts/hyperlex.py demo
```

Expect `ok: true`, a receipt path, a lineage for known slang (for example `rizz` → `brainrot-aura`), and **`brier: null`**.

### Install the Hermes skill

```bash
bash install.sh --dry-run && bash install.sh
export HERMES_SKILL_DIR="${HOME}/.hermes/skills/hyperlex"
export HLX="python3 $HERMES_SKILL_DIR/scripts/hyperlex.py"

$HLX check && $HLX doctor && $HLX demo
$HLX wizard --auto
```

Optional Claude Code host (additive; Hermes stays primary):

```bash
bash install.sh --claude
export HYPERLEX_SKILL_DIR="${HOME}/.claude/skills/hyperlex"
export HLX="python3 $HYPERLEX_SKILL_DIR/scripts/hyperlex.py"
$HLX demo
```

Optional editable package: `pip install -e ".[dev]"` then `python -m hyperlex check`.

Full path: [docs/start/quickstart.md](./docs/start/quickstart.md) · [docs/install-package.md](./docs/install-package.md)

---

## Atlas

How the pieces sit together as of **v0.4.0**:

```text
                    ┌──────────────────────────────────────┐
                    │            HERMES SKILL              │
                    │    SKILL.md · scripts/hyperlex.py    │
                    └──────────────────┬───────────────────┘
                                       │
     ┌─────────────────────────────────┼─────────────────────────────────┐
     ▼                                 ▼                                 ▼
┌──────────┐                    ┌────────────┐                    ┌────────────┐
│  INTAKE  │  --route offline   │  ANALYSIS  │                    │  RESEARCH  │
│  routes  │  --route live ──►  │  8 families│                    │  Phase 5   │
│  mock ·  │                    │  virality  │                    │  simulate  │
│  glossary│                    │  hyperstit.│                    │  SPECULATIVE│
│  social  │                    └──────┬─────┘                    └──────┬─────┘
└──────────┘                           │                                 │
                                       ▼                                 │
                                ┌────────────┐                           │
                                │  RECEIPT   │  hash · ledger            │
                                │  FORECAST  │  p only, no Brier         │
                                └──────┬─────┘                           │
                                       ▼                                 │
                                ┌────────────┐     ┌──────────┐          │
                                │  SETTLE    │ ──► │  BRIER   │          │
                                │  operator  │     │  series  │          │
                                └────────────┘     └──────────┘          │
                                       │                                 │
                    ┌──────────────────┴─────────────────┬───────────────┘
                    ▼                                    ▼
             ~/.hyperlex/                         docs/archive/  (Pages)
             receipts · score log                 sanitized history
             vector.db · cache                    not the live DB

                    ┌──────────────────────────────────────┐
                    │  SHADOW · Spec 007 Hyperlexical      │
                    │  scripts/shadow/hyperlexical/        │
                    │  advisory only · not API_V1          │
                    │  name_gate = false · E2 Spark-blocked│
                    └──────────────────────────────────────┘
```

| Zone | What lives here |
|------|-----------------|
| **Intake** | Named routes (`offline` / `live` / `glossary` / `social`). Offline forces mock. |
| **Analysis** | Neologisms, **8** lineage families + 2026 YTD leaves, typology, virality, hyperstition stage. No ninth family. |
| **Receipt** | Integrity-hashed JSON + append-only ledger under `~/.hyperlex/`. |
| **Calibration** | `pending` → `settle` → `score-series` (only place Brier is real). |
| **Research** | Phase 5 transmission, multi-agent, risk, phylogeny — always **SPECULATIVE**. |
| **SHADOW 007** | Learned encoder harness. Classify volume is ready. `name_gate` stays **false** until E2 passes on Spark. Not named Hyperlexical. No Hub publish. |

---

## Hard rules

1. **Brier requires settlement** — open analysis always has `provenance.brier = null`.
2. **Phase 5 is SPECULATIVE** — sim packets keep `brier: null`.
3. **Spec 007 is SHADOW** — advisory packets only. Do not treat stub or Spark seed smoke as a named model.
4. **No Abraxas hard dependency** — hosts may import *from* Hyperlex.
5. **Local is source of truth** — Pages is sanitized history only.
6. **Cron is advisory** — `risk-schedule` proposes jobs; operators register them.

---

## Daily path

One command runs ingest through results. Settlement stays human.

```bash
# AUTO: ingest → analyze → receipt → forecasts → score log → Phase 5 risk
$HLX pipeline "rizz" --route offline
$HLX pipeline "sigma rizz locked in"   # expands to atoms

$HLX pending
$HLX settle --forecast-id <id> --decision TRUE   # FALSE | VOID | CONFLICT
$HLX score-series --mean-shift --verify-chain
```

Ingest routes: `offline` (no network) · `live` · `glossary` · `social`.  
`HYPERLEX_OFFLINE=1` forces mock for any network source. See `$HLX sources`.

Scan + advisory cron, vector seed, and Phase 5 `simulate` are optional. Command map: [docs/commands.md](./docs/commands.md). Operator burn-in: [docs/operator-loop.md](./docs/operator-loop.md).

---

## Status (2026-09-10)

| Area | State |
|------|--------|
| Skill + offline pipeline + settle loop | Ready |
| Lineage | **8** families + 2026 YTD leaves |
| Phase 5 research sim | Ready (SPECULATIVE) |
| Spec 007 encoder | SHADOW on main. Classify volume ready. **`name_gate` false.** E2 Spark-blocked. No Hub. Not named Hyperlexical. |
| Public PyPI | Not planned |

Spark bring-up procedure (seed smoke, not a card): [SPARK-BRINGUP.md](./specs/007-hyperlexical-model/SPARK-BRINGUP.md) · [AARON-SPARK-TRAIN.md](./specs/007-hyperlexical-model/AARON-SPARK-TRAIN.md).

[STATUS.md](./STATUS.md) · [ROADMAP.md](./ROADMAP.md) · [CHANGELOG.md](./CHANGELOG.md)

---

## Docs

Published site: [scrimshawlife-ctrl.github.io/Hyperlex](https://scrimshawlife-ctrl.github.io/Hyperlex/)

| Need | Go |
|------|-----|
| First success | [Quickstart](./docs/start/quickstart.md) · [See it work](./docs/start/see-it-work.md) |
| Jargon + constraints | [Glossary](./docs/start/glossary.md) |
| Commands / burn-in | [Command map](./docs/commands.md) · [Operator loop](./docs/operator-loop.md) |
| Lineage | [Slang lineages](./docs/slang-lineages.md) |
| Spec 007 (SHADOW) | [SHADOW encoder](./docs/shadow-hyperlexical.md) · [Spec kit](./specs/README.md) |
| Architecture spine | [ARCHITECTURE.md](./ARCHITECTURE.md) (historical 0.2.x stamp; current skill is 0.4.0) |

Root files `QUICKSTART.md`, `ARCHITECTURE.md`, `DESIGN.md`, and `SPEC.md` stay as history. Prefer the docs site for navigation.

---

## Contribute

See [CONTRIBUTING.md](./CONTRIBUTING.md). Keep the settlement rule and offline-first defaults. Do not invent Brier, a ninth lineage family, a Hub card, or `name_gate: true`.

```bash
PYTHONPATH=src python3 -m pytest -q
pip install -e ".[docs]" && mkdocs serve
```

---

## License

MIT — [LICENSE](./LICENSE).

Built for operators who want memetic signal **with a receipt trail**, not a mood board.
