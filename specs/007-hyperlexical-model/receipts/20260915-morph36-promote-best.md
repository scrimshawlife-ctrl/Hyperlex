# Receipt — morph36 → BEST (operator grant)

**Date:** 2026-09-15  
**Authority:** Operator continue — *YES promote morph36 KEEP_CANDIDATE → BEST*.  
**`promote_best=true` this once.** `name_gate=false`. No Hub. SHADOW OK.

## Decision

| check | result |
|-------|--------|
| morph36 best unbind_exact | **0.5455** (ep23, saved primary) |
| prior BEST morph19 | **0.4545** |
| beats prior BEST? | **Yes** (0.5455 > 0.4545) |
| Operator promote yes? | **Yes** (this turn) |
| morph19 artifacts preserved? | **Yes** (dir + `model.safetensors` mtime unchanged) |

## Pin after promote

| pin | path |
|-----|------|
| **BEST** | `~/.hyperlex/models/BEST` → `...-seed-morph36` |
| prior BEST (preserved) | `...-seed-morph19` (intact; not deleted) |
| morph35 KEEP | still on disk |

## Scores (civilian n=363)

| model | unbind_exact | token_f1 | slot_f1 |
|-------|-------------:|---------:|--------:|
| morph19 (prior BEST) | 0.4545 | 0.6976 | 0.6966 |
| **morph36 BEST (ep23)** | **0.5455** | **0.7714** | **0.7714** |

Ladder **≥0.55**: still **MISS** (0.5455).

## Artifacts

- Spark private: `~/hlx-private/p1-spark-morph36-promote-best-20260915/`
- Workspace: `specs/007-hyperlexical-model/receipts/morph36-promote-best-20260915/`
- `promote-best-receipt.json` records operator grant + prior BEST=morph19

## Policy hold

- Do **not** invent OBSERVED `partial_slot_miss` gold (Danny still required)
- `name_gate=false` / no Hub / no Hyperlexical name card
