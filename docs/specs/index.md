# Spec kit

Hyperlex **runs as a Hermes skill** today. Spec 007 is the **model path** (T0 → T1 after E2), still SHADOW.

**Naming:** **Hyperlexical** = Spec 007 model / train / eval / E2 / `name_gate` claim. **ne0l0gist** = slang ingest / harvest. Repo **Hyperlex** is the transitional monorepo shell. `name_gate` stays false.

Specs live under [`specs/`](https://github.com/scrimshawlife-ctrl/Hyperlex/tree/main/specs) in the repository. This page is the docs-site index. It does not add gates.

Constitution: [`.specify/memory/constitution.md`](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/.specify/memory/constitution.md) (v1.0.0, **SHADOW** until operator promotion).

| ID | Title | SDD status | Runtime on main |
|----|-------|------------|-----------------|
| 000 | Hyperlex spine (as-built v0.4.0) | SPECIFY locked | shipping |
| 001 | Mutation grammar detector | CLARIFY locked · implement on main · not CONVERGED | `hyperlex.mutation` + tests |
| 002 | Hermes command surface | SPECIFY locked · implement partial | package CLI + `hlx-mutation` + `hyperlex init` |
| 003 | Mutation detect v0.2 | SPECIFY locked · implement SHADOW | GAME_ENCODE / CODE_SWITCH / PHONETIC_WARP + watch jsonl + `--human` |
| 004 | Recoverable-structure probe | SPECIFY locked · implement SHADOW | `scripts/shadow/recoverable_structure/` |
| 005 | Route labels | SPECIFY locked (Notion + branch `005-route-labels`) | not on main — [PR 18](https://github.com/scrimshawlife-ctrl/Hyperlex/pull/18) |
| 006 | IsA | reserved — do not open from 007 | — |
| 007 | Hyperlexical model | SPECIFY locked C1–C52 · A5 milestones · SHADOW implement on main | `scripts/shadow/hyperlexical/` · E2 fail · `name_gate` false · no Hub |

## Spec 007 (SHADOW)

Not on `API_V1`. Not a Hugging Face model. Not named **Hyperlexical** until E2 passes on Spark.

- Pages overview: [SHADOW encoder (007)](../shadow-hyperlexical.md)
- Operator snapshot: [Status](../status.md)
- Spark bring-up (procedure, not a card): [SPARK-BRINGUP.md](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/specs/007-hyperlexical-model/SPARK-BRINGUP.md)
- Aaron train spec: [AARON-SPARK-TRAIN.md](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/specs/007-hyperlexical-model/AARON-SPARK-TRAIN.md)
- A5 milestones: [milestones.md](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/specs/007-hyperlexical-model/milestones.md)
- Harvest receipts: [KEEP-93](../receipts/settle-keep93-2026-09-10.md) · [Blanket-yes unlock](../receipts/blanket-yes-unlock-2026-09-10.md)

## Historical spine

The v0.3 technical spec is mirrored at [Technical spec](../spec.md). Current skill version is **0.4.0**. Prefer [Commands](../commands.md) and [Status](../status.md) for what ships today.
