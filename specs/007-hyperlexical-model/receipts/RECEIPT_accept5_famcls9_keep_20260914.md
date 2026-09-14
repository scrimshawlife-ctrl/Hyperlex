# RECEIPT — accept5 hygiene + famcls9 KEEP (2026-09-14)

**Authority:** Spec 007. Agent classification ownership.
**BEST:** untouched. `name_gate` false.

## Accept5 (data)

Parent: accept4.

| action | n |
|--------|---|
| relabel ai-native → brainrot-aura | 105 |
| dedupe drop duplicate family rows | 101 |
| prepare rows after | 629 |

Pin: `~/hlx-private/p1-classify-accept5-20260914/prepare`.

## Famcls9 (weights)

Recipe: init famcls → freeze encoder+structure → family-head inv-freq CE (40 ep).

Pre-registered gate: family > famcls accept5 baseline (0.196) AND structure/role/pointer = 1.0.

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls baseline | 1.0 | 1.0 | 1.0 | 0.196 |
| **famcls9** | **1.0** | **1.0** | **1.0** | **0.500** |

**KEEP.** Family Δ +0.304 with full structure hold.

## Pins after

- Weights: famcls9
- Data: accept5
- BEST: morph19 unchanged

## Artifacts

- `~/hlx-private/p1-classify-accept5-20260914/`
- `~/hlx-private/p1-structure-unbind-famcls9-20260914/{KEPT.md,SMOKE_SUMMARY.json,GATE.md,out/}`
