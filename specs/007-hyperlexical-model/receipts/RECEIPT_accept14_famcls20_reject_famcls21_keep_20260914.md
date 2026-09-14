# RECEIPT — accept14 + famcls20 REJECT + famcls21 KEEP (2026-09-14)

**Authority:** Spec 007. Agent classification ownership.
**BEST:** untouched. `name_gate` false.

## Context

Merged famcls19 KEEP on accept13 (family 0.805). Confusion dump → residual-miss accept14 (+188 promoted).
Fair famcls19 on accept14-test family **0.7846** (structure/role/pointer 1.0).

## Famcls20 (REJECT)

Recipe: init famcls19 → freeze structure → family head + last **N=4** encoder layers.
Gate needed family > 0.7846. Got **0.7769**. Structure held. **REJECT** (same-N plateau/regress).

## Famcls21 (KEEP) — new recipe

Recipe: init famcls19 → freeze structure → family head + last **N=6** encoder layers.
Inv-freq CE. Encoder LR **1e-5**, head LR 1e-3, 40 ep (best epoch 2).

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls19 baseline | **1.0** | **1.0** | **1.0** | **0.7846** |
| famcls20 (N=4) | 1.0 | 1.0 | 1.0 | 0.7769 |
| **famcls21 (N=6)** | **1.0** | **1.0** | **1.0** | **0.8000** |

**KEEP.** Family Δ **+0.015**. Structure hold OK. BEST unchanged.

## Pins after

- Weights: **famcls21** (`~/hlx-private/p1-structure-unbind-famcls21-20260914/`)
- Data: **accept14** (`~/hlx-private/p1-classify-accept14-20260914/prepare`)
- BEST: morph19 unchanged

## Artifacts

- `~/hlx-private/p1-structure-unbind-famcls20-20260914/REJECTED.md`
- `~/hlx-private/p1-structure-unbind-famcls21-20260914/{KEPT.md,GATE.md,SMOKE_SUMMARY.json,out/}`
- `~/hlx-private/p1-classify-accept14-20260914/{prepare,famcls19_on_accept14_eval.json}`

## Lesson

When last-N=4 stopped clearing the fair gate, deepening to last-N=6 with the same safe encoder LR unlocked KEEP without spending structure — same pattern as the earlier N=2→N=4 unlock.
