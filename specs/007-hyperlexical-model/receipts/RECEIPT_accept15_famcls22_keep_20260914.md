# RECEIPT — accept15 + famcls22 KEEP (2026-09-14)

**Authority:** Spec 007. Agent classification ownership.
**BEST:** untouched. `name_gate` false.

## Context

Merged famcls21 KEEP on accept14 (family 0.800). Confusion dump → residual-miss accept15 (+79 promoted).
Fair famcls21 on accept15-test family **0.8169** (structure/role/pointer 1.0).

## Famcls22 (weights)

Recipe: init famcls21 → freeze structure → family head + last **N=6** encoder layers.
Inv-freq CE. Encoder LR **1e-5**, head LR 1e-3, 40 ep (best epoch 22).

Pre-registered gate: family > 0.8169 (famcls21 accept15-test) AND structure/role/pointer = 1.0.

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls21 baseline | **1.0** | **1.0** | **1.0** | **0.8169** |
| **famcls22 (N=6)** | **1.0** | **1.0** | **1.0** | **0.8310** |

**KEEP.** Family Δ **+0.014**. Structure hold OK. BEST unchanged.

## Pins after

- Weights: **famcls22** (`~/hlx-private/p1-structure-unbind-famcls22-20260914/`)
- Data: **accept15** (`~/hlx-private/p1-classify-accept15-20260914/prepare`)
- BEST: morph19 unchanged

## Artifacts

- `~/hlx-private/p1-structure-unbind-famcls22-20260914/{KEPT.md,GATE.md,SMOKE_SUMMARY.json,out/}`
- `~/hlx-private/p1-classify-accept15-20260914/{prepare,famcls21_on_accept15_eval.json}`

## Lesson

Same last-N=6 recipe continued to clear the fair gate on residual-miss gold without spending structure; family line now above **0.83** on the held-out accept15-test.
