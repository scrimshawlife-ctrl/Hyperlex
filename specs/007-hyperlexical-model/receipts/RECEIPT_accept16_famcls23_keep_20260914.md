# RECEIPT — accept16 + famcls23 KEEP (2026-09-14)

**Authority:** Spec 007. Agent classification ownership.
**BEST:** untouched. `name_gate` false.

## Context

Merged famcls22 KEEP on accept15 (family 0.831). Confusion dump → residual-miss accept16 (+70 promoted).
Fair famcls22 on accept16-test family **0.8400** (structure/role/pointer 1.0).

## Famcls23 (weights)

Recipe: init famcls22 → freeze structure → family head + last **N=6** encoder layers.
Inv-freq CE. Encoder LR **1e-5**, head LR 1e-3, 40 ep (best epoch 39 / last-epoch fallback).

Pre-registered gate: family > 0.84 (famcls22 accept16-test) AND structure/role/pointer = 1.0.

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls22 baseline | **1.0** | **1.0** | **1.0** | **0.8400** |
| **famcls23 (N=6)** | **1.0** | **1.0** | **1.0** | **0.8533** |

**KEEP.** Family Δ **+0.013**. Structure hold OK. BEST unchanged.

## Pins after

- Weights: **famcls23** (`~/hlx-private/p1-structure-unbind-famcls23-20260914/`)
- Data: **accept16** (`~/hlx-private/p1-classify-accept16-20260914/prepare`)
- BEST: morph19 unchanged

## Artifacts

- `~/hlx-private/p1-structure-unbind-famcls23-20260914/{KEPT.md,GATE.md,SMOKE_SUMMARY.json,out/}`
- `~/hlx-private/p1-classify-accept16-20260914/{prepare,famcls22_on_accept16_eval.json}`

## Lesson

Same last-N=6 recipe continued to clear the fair gate on residual-miss gold without spending structure; family line now above **0.85** on the held-out accept16-test.
