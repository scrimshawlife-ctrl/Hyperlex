# Spec 007 — after famcls4 reject; pause train thrash

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins (unchanged)

| pin | path | note |
|-----|------|------|
| **weight joint** | `~/hlx-private/p1-structure-unbind-famcls-20260914/` | structure/role/pointer **1.0**; accept-test family **0.659** |
| **data pin** | `~/hlx-private/p1-classify-accept-20260914/prepare` | +18 operator-accepted labels |
| structure reference | `~/hlx-private/p1-structure-unbind-famsel-20260914/` | prior structure-line keep |

## Rejected ladder (family resume)

| run | result |
|-----|--------|
| famcls2 | structure/pointer regress |
| famcls3 | family 0.636 < famcls 0.659 on accept-test |
| **famcls4** | frozen family-head; family **0.591** < 0.659 |

## Policy

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. **Pause** further CE / sampler / head climbs on current gold
4. Next progress = **new reviewed labels** (especially `none`) or an explicitly new recipe hypothesis with a pre-registered gate

## Next (operator)

1. Review remaining INFERRED queue / add `none` OBSERVED shorts if available
2. File accepted label deltas → rebuild accept prepare → resume only with gate family > **0.659** + structure hold
3. Hold envelope morphs / BEST overwrite
