# RECEIPT — accept6 targeted gold + famcls10 reject (2026-09-14)

**Authority:** Spec 007. Agent classification ownership.
**BEST:** untouched. `name_gate` false.

## Famcls9 confusion (accept5-test)

family_exact **0.500**, 23 mistakes — mainly `brainrot-aura → gaming-meta`, crypto mixups, thin workplace/political.

## Accept6 (data)

Parent: accept5. **+171** agent-targeted weak-family surfaces.

| family | n |
|--------|---|
| crypto-degen | 25 |
| none | 24 |
| brainrot-aura | 23 |
| workplace-corp | 19 |
| gaming-meta | 19 |
| betting-sharp | 17 |
| kinship-address | 16 |
| political-status | 16 |
| ai-native | 12 |

Pin: `~/hlx-private/p1-classify-accept6-20260914/prepare`.

## Famcls10 (weights)

Recipe: init famcls9 → freeze encoder+structure → family-head inv-freq CE (40 ep).

Pre-registered gate: family > 0.481 (famcls9 accept6-test) AND structure/role/pointer = 1.0.

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls9 baseline | **1.0** | **1.0** | **1.0** | **0.481** |
| famcls10 | **1.0** | **1.0** | **1.0** | 0.463 |

**REJECT.** Family Δ −0.019. Structure hold OK.

## Pins after

- Weights: **famcls9** (unchanged)
- Data: **accept6**
- BEST: morph19 unchanged

## Artifacts

- `~/hlx-private/p1-classify-accept6-20260914/`
- `~/hlx-private/p1-structure-unbind-famcls10-20260914/{REJECTED.md,SMOKE_SUMMARY.json,GATE.md,out/}`
