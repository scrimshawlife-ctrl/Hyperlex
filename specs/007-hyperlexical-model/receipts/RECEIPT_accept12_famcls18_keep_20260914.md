# RECEIPT — accept12 + famcls18 KEEP (2026-09-14)

**Authority:** Spec 007. Agent classification ownership.
**BEST:** untouched. `name_gate` false.

## Context

famcls17 KEEP on accept11 (family 0.713). Confusion dump → novel residual-miss accept12 (+315 promoted).
Fair famcls17 on accept12-test family **0.7170** (structure/role/pointer 1.0).

## Famcls18 (weights)

Recipe: init famcls17 → freeze structure → family head + last **N=4** encoder layers.
Inv-freq CE. Encoder LR **1e-5**, head LR 1e-3, 40 ep (best epoch 2).

Pre-registered gate: family > 0.7170 (famcls17 accept12-test) AND structure/role/pointer = 1.0.

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls17 baseline | **1.0** | **1.0** | **1.0** | **0.7170** |
| **famcls18 (N=4)** | **1.0** | **1.0** | **1.0** | **0.7736** |

**KEEP.** Family Δ **+0.057**. Structure hold OK. BEST unchanged.

## Pins after

- Weights: **famcls18** (`~/hlx-private/p1-structure-unbind-famcls18-20260914/`)
- Data: **accept12** (`~/hlx-private/p1-classify-accept12-20260914/prepare`)
- BEST: morph19 unchanged

## Artifacts

- `~/hlx-private/p1-structure-unbind-famcls18-20260914/{KEPT.md,GATE.md,SMOKE_SUMMARY.json,out/}`
- `~/hlx-private/p1-classify-accept12-20260914/{prepare,famcls17_on_accept12_eval.json}`

## Lesson

Same last-N=4 recipe continued to clear the fair gate on expanded novel residual-miss gold without spending structure (early best epoch 2 under structure guard); largest recent family Δ (+0.057).
