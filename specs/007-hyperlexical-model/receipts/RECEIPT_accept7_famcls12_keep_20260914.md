# RECEIPT — accept7 MERGED + famcls12 KEEP (2026-09-14)

**Authority:** Spec 007. Agent classification ownership.
**BEST:** untouched. `name_gate` false.

## Merge

Operator: merge and continue as recommended.
- Data pin → **accept7**
- Rejected audit: famcls10 (CE head-only), famcls11 (hard-neg head-only)
- Recommended unlock: encoder last-N under structure hold

## Famcls12 (weights)

Recipe: init famcls9 → freeze structure heads → train family head + last **N=2** encoder layers (inv-freq CE; enc LR 2e-5; head LR 1e-3).

Pre-registered gate: family > 0.452 (famcls9 accept7-test) AND structure/role/pointer = 1.0.

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls9 baseline | **1.0** | **1.0** | **1.0** | **0.452** |
| **famcls12** | **1.0** | **1.0** | **1.0** | **0.516** |

**KEEP.** Family Δ **+0.065**. Structure hold OK. BEST unchanged.

## Pins after

- Weights: **famcls12**
- Data: **accept7**
- BEST: morph19 unchanged

## Artifacts

- `~/hlx-private/p1-classify-accept7-20260914/`
- `~/hlx-private/p1-structure-unbind-famcls12-20260914/{KEPT.md,GATE.md,out/}`

## Lesson

Head-only climbs failed the fair gate; moving last-N encoder layers cleared family while holding structure at 1.0.
