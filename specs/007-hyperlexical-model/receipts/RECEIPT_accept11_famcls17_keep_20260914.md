# RECEIPT — accept11 + famcls17 KEEP (2026-09-14)

**Authority:** Spec 007. Agent classification ownership.
**BEST:** untouched. `name_gate` false.

## Context

famcls16 KEEP on accept10 (family 0.686). Confusion dump → residual-miss accept11 (+225 promoted).
Fair famcls16 on accept11-test family **0.6809** (structure/role/pointer 1.0).

## Famcls17 (weights)

Recipe: init famcls16 → freeze structure → family head + last **N=4** encoder layers.
Inv-freq CE. Encoder LR **1e-5**, head LR 1e-3, 40 ep (best epoch 2).

Pre-registered gate: family > 0.6809 (famcls16 accept11-test) AND structure/role/pointer = 1.0.

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls16 baseline | **1.0** | **1.0** | **1.0** | **0.6809** |
| **famcls17 (N=4)** | **1.0** | **1.0** | **1.0** | **0.7128** |

**KEEP.** Family Δ **+0.032**. Structure hold OK. BEST unchanged.

## Pins after

- Weights: **famcls17** (`~/hlx-private/p1-structure-unbind-famcls17-20260914/`)
- Data: **accept11** (`~/hlx-private/p1-classify-accept11-20260914/prepare`)
- BEST: morph19 unchanged

## Artifacts

- `~/hlx-private/p1-structure-unbind-famcls17-20260914/{KEPT.md,GATE.md,SMOKE_SUMMARY.json,out/}`
- `~/hlx-private/p1-classify-accept11-20260914/{prepare,famcls16_on_accept11_eval.json}`

## Lesson

Same last-N=4 recipe continued to clear the fair gate on expanded residual-miss gold without spending structure (early best epoch 2 under structure guard).
