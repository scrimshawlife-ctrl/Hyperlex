# RECEIPT — accept8 MERGED + famcls13 KEEP (2026-09-14)

**Authority:** Spec 007. Agent classification ownership.
**BEST:** untouched. `name_gate` false.

## Merge

Operator: merge and continue.
- Weight pin was famcls12 KEEP
- Built accept8 from famcls12 accept7-test remaining 30 mistakes (+192)
- Climbed famcls13 last-N from famcls12 under structure hold

## Fair accept8-test

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls12 baseline | **1.0** | **1.0** | **1.0** | **0.543** |
| **famcls13** | **1.0** | **1.0** | **1.0** | **0.614** |

**KEEP.** Family Δ **+0.071**. Structure hold OK. BEST unchanged.

## Pins after

- Weights: **famcls13**
- Data: **accept8**
- BEST: morph19 unchanged

## Artifacts

- `~/hlx-private/p1-classify-accept8-20260914/`
- `~/hlx-private/p1-structure-unbind-famcls13-20260914/{KEPT.md,GATE.md,out/}`

## Lesson

Miss-targeted gold + last-N encoder recipe continues to clear fair gates with structure hold, where head-only climbs failed.
