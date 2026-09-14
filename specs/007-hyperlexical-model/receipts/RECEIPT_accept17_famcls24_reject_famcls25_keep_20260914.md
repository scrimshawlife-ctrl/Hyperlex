# RECEIPT — accept17 + famcls24 REJECT + famcls25 KEEP (2026-09-14)

**Authority:** Spec 007. Agent classification ownership.
**BEST:** untouched. `name_gate` false.

## Context

Merged famcls23 KEEP on accept16 (family 0.853). Confusion dump → residual-miss accept17 (+261 promoted).
Fair famcls23 on accept17-test family **0.8607594936708861** (structure/role/pointer 1.0).

## Famcls24 (N=6) — REJECT

Recipe: init famcls23 → freeze structure → family head + last **N=6** encoder layers.
Inv-freq CE. Encoder LR **1e-5**, head LR 1e-3, **full 40 epochs** (selection epoch 4).

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls23 baseline | **1.0** | **1.0** | **1.0** | **0.8608** |
| famcls24 (N=6) | **0.9583** | **1.0** | **0.9583** | **0.8608** |

**REJECT.** Family tie. Structure/pointer slip.

## Protocol change

Deepen **last-N 6→8**; init famcls23; same accept17; full 40 epochs.

## Famcls25 (N=8) — KEEP

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls23 baseline | **1.0** | **1.0** | **1.0** | **0.8608** |
| **famcls25 (N=8)** | **1.0** | **1.0** | **1.0** | **0.9304** |

**KEEP.** Family Δ **+0.0696**. Structure hold OK. BEST unchanged. Full 40 epochs completed (best epoch 7).

## Pins after

- Weights: **famcls25** (`~/hlx-private/p1-structure-unbind-famcls25-20260914/`)
- Data: **accept17** (`~/hlx-private/p1-classify-accept17-20260914/prepare`)
- BEST: morph19 unchanged

## Artifacts

- `~/hlx-private/p1-structure-unbind-famcls24-20260914/{REJECTED.md,GATE.md,SMOKE_SUMMARY.json,out/}`
- `~/hlx-private/p1-structure-unbind-famcls25-20260914/{KEPT.md,GATE.md,SMOKE_SUMMARY.json,out/}`
- `~/hlx-private/p1-classify-accept17-20260914/{prepare,famcls23_on_accept17_eval.json}`

## Lesson

Same-N=6 plateau + structure slip → deepen to N=8 restored structure hold and unlocked a large family lift. Mandate full 40-epoch runs.
