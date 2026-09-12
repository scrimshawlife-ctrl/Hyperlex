# Hyperlex Spec Kit

Constitution: `.specify/memory/constitution.md` (v1.0.0, **SHADOW** until operator promotion)

| ID | Title | SDD status | Runtime on main |
|----|-------|------------|-----------------|
| 000 | Hyperlex spine (as-built v0.4.0) | SPECIFY locked | shipping |
| 001 | Mutation grammar detector | CLARIFY locked · implement on main · not CONVERGED | `hyperlex.mutation` + tests |
| 002 | Hermes command surface | SPECIFY locked · implement partial | package CLI + `hlx-mutation` + `hyperlex init` |
| 003 | Mutation detect v0.2 | SPECIFY locked · implement SHADOW | GAME_ENCODE / CODE_SWITCH / PHONETIC_WARP + watch jsonl + `--human` |
| 004 | Recoverable-structure probe | SPECIFY locked · implement SHADOW | `scripts/shadow/recoverable_structure/` |
| 005 | Route labels | SPECIFY locked (Notion + branch `005-route-labels`) | not on main — PR 18 |
| 006 | IsA | reserved — do not open from 007 | — |
| 007 | Hyperlexical model | SPECIFY locked C1–C52 · A5 milestones/engineering · SHADOW implement on main | `scripts/shadow/hyperlexical/` + Aaron Spark handoff. E2 fail. No Hub. |

007 extras: `clarify.md`, `locks-a4.md`, `locks-a5.md`, `weights.md`, `hardware.md`, `uncensored.md`, `trunk.md`, `AARON-SPARK-TRAIN.md`, `milestones.md`, `engineering.md`, `hf-package/`, `schemas/`, `contracts/`.

Naming (2026-09-12): **Hyperlexical** = Spec 007 model / train / eval / E2 / `name_gate` claim. **ne0l0gist** = slang ingest / harvest. Repo **Hyperlex** is the transitional monorepo shell. `name_gate` stays false.

Handoff: `specs/007-hyperlexical-model/AARON-SPARK-TRAIN.md` on **main**.

Gate: `specs/runtime-ready.md`
