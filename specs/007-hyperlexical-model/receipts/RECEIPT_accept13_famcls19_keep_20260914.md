# RECEIPT — accept13 + famcls19 KEEP (2026-09-14)

**Authority:** Spec 007. Agent classification ownership.
**BEST:** untouched. `name_gate` false.

## Context

Merged famcls18 KEEP on accept12 (family 0.774). Confusion dump → residual-miss accept13 (+161 promoted).
Fair famcls18 on accept13-test family **0.7712** (structure/role/pointer 1.0).

## Famcls19 (weights)

Recipe: init famcls18 → freeze structure → family head + last **N=4** encoder layers.
Inv-freq CE. Encoder LR **1e-5**, head LR 1e-3, 40 ep (best epoch 12).

Pre-registered gate: family > 0.7712 (famcls18 accept13-test) AND structure/role/pointer = 1.0.

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls18 baseline | **1.0** | **1.0** | **1.0** | **0.7712** |
| **famcls19 (N=4)** | **1.0** | **1.0** | **1.0** | **0.8051** |

**KEEP.** Family Δ **+0.034**. Structure hold OK. BEST unchanged.

## Pins after

- Weights: **famcls19** (`~/hlx-private/p1-structure-unbind-famcls19-20260914/`)
- Data: **accept13** (`~/hlx-private/p1-classify-accept13-20260914/prepare`)
- BEST: morph19 unchanged

## Artifacts

- `~/hlx-private/p1-structure-unbind-famcls19-20260914/{KEPT.md,GATE.md,SMOKE_SUMMARY.json,out/}`
- `~/hlx-private/p1-classify-accept13-20260914/{prepare,famcls18_on_accept13_eval.json}`

## Lesson

Same last-N=4 recipe continued to clear the fair gate on residual-miss gold without spending structure; family line now above **0.80** on the held-out accept13-test.
