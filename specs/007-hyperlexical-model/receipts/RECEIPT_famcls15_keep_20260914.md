# RECEIPT — famcls15 KEEP last-N=4 on accept9 (2026-09-14)

**Authority:** Spec 007. Agent classification ownership.
**BEST:** untouched. `name_gate` false.

## Context

famcls14 last-N=2 on accept9 tied fair baseline 0.615 → REJECT.
Continue with **new** pre-registered recipe: last-N=4 + lower encoder LR.

## Famcls15 (weights)

Recipe: init famcls13 → freeze structure → family head + last **N=4** encoder layers.
Inv-freq CE. Encoder LR **1e-5**, head LR 1e-3, 40 ep.

Pre-registered gate: family > 0.615 (famcls13 accept9-test) AND structure/role/pointer = 1.0.

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls13 baseline | **1.0** | **1.0** | **1.0** | **0.615** |
| famcls14 (N=2) | 1.0 | 1.0 | 1.0 | 0.615 |
| **famcls15 (N=4)** | **1.0** | **1.0** | **1.0** | **0.641** |

**KEEP.** Family Δ **+0.026**. Structure hold OK. BEST unchanged.

## Pins after

- Weights: **famcls15**
- Data: **accept9**
- BEST: morph19 unchanged

## Artifacts

- `~/hlx-private/p1-structure-unbind-famcls15-20260914/{KEPT.md,GATE.md,out/}`
- `~/hlx-private/p1-classify-accept9-20260914/prepare`

## Lesson

When last-N=2 plateaued, deepening to last-N=4 with a safer encoder LR cleared the fair gate without spending structure.
