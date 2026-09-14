# RECEIPT — accept10 + famcls16 KEEP (2026-09-14)

**Authority:** Spec 007. Agent classification ownership.
**BEST:** untouched. `name_gate` false.

## Context

famcls15 KEEP on accept9 (family 0.641). Confusion dump → residual-miss accept10 (+94 promoted).
Fair famcls15 on accept10-test family **0.6628** (structure/role/pointer 1.0).

## Famcls16 (weights)

Recipe: init famcls15 → freeze structure → family head + last **N=4** encoder layers.
Inv-freq CE. Encoder LR **1e-5**, head LR 1e-3, 40 ep (best epoch 39).

Pre-registered gate: family > 0.6628 (famcls15 accept10-test) AND structure/role/pointer = 1.0.

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls15 baseline | **1.0** | **1.0** | **1.0** | **0.6628** |
| **famcls16 (N=4)** | **1.0** | **1.0** | **1.0** | **0.6860** |

**KEEP.** Family Δ **+0.023**. Structure hold OK. BEST unchanged.

## Pins after

- Weights: **famcls16** (`~/hlx-private/p1-structure-unbind-famcls16-20260914/`)
- Data: **accept10** (`~/hlx-private/p1-classify-accept10-20260914/prepare`)
- BEST: morph19 unchanged

## Artifacts

- `~/hlx-private/p1-structure-unbind-famcls16-20260914/{KEPT.md,GATE.md,SMOKE_SUMMARY.json,out/}`
- `~/hlx-private/p1-classify-accept10-20260914/{prepare,famcls15_on_accept10_eval.json}`

## Lesson

Same last-N=4 recipe continued to clear the fair gate on expanded residual-miss gold without spending structure.
