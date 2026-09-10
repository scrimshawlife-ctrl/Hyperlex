# Hyperlex Spec Kit

Constitution: `.specify/memory/constitution.md` (v1.0.0, **SHADOW** until operator promotion)

| ID | Title | SDD status | Runtime on main |
|----|-------|------------|-----------------|
| 000 | Hyperlex spine (as-built v0.4.0) | SPECIFY locked | shipping |
| 001 | Mutation grammar detector | CLARIFY locked · implement on main · not CONVERGED | `hyperlex.mutation` + tests |
| 002 | Hermes command surface | SPECIFY locked · implement partial | package CLI + `hlx-mutation` + `hyperlex init` |
| 003 | Mutation detect v0.2 | SPECIFY locked · implement SHADOW | GAME_ENCODE / CODE_SWITCH / PHONETIC_WARP + watch jsonl + `--human` |
| 004 | Recoverable-structure probe | SPECIFY locked · implement SHADOW | `scripts/shadow/recoverable_structure/` |
| 005 | Route labels | SPECIFY locked (Notion + branch `005-route-labels`) | not on main |
| 006 | IsA | reserved — do not open from 007 | — |
| 007 | Hyperlexical model | SPECIFY locked · SHADOW · implement not started | none (specs only) |

001 extras: `clarify.md`, `threat-model.md`, `owasp-mapping.md`, `checklist.md`, `dual-use-gate.md`, `ux-commands.md`, `schemas/mutation_trace.v0.1.schema.json`

003 extras: `dual-use-gate.md` (L4/L6 detect-only addendum). Packet schema stays `hyperlex.mutation_trace.v0.1`. Constitution stays SHADOW.

007 extras: `clarify.md` C1–C12, `plan.md`, `tasks.md`, `checklist.md`, `dual-use-gate.md`, `schemas/hyperlexical_inference.v0.1.schema.json`. Packet hard-nulls Brier. Does not claim `semantic`. Does not open 006.

Gate: `specs/runtime-ready.md`

Merged PRs that landed the gate: #6 detector, #7–9 skill alias, #10 wheel, #11 graft-style init.
