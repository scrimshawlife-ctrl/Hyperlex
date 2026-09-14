# Receipt — structure recipe change: unbind pointer (2026-09-14)

SHADOW / `name_gate=false`. No Hub. No BEST overwrite.

## Action
Operator **continue** after expanded-gold miss: change structure recipe.

- Root cause: closed-vocab filler CE vs OOV holdout fillers
- Recipe: CLS+slot unbind; role CE; filler span-pointer
- Schemes unchanged: `positional` | `type_slot`
- Prepare reused: `~/hlx-private/p1-structure-dual-expanded-prepare-20260914/`
- Out: `~/hlx-private/p1-structure-unbind-pointer-20260914/out`

## Metrics
| split | structure_exact | role_exact | filler_pointer_exact |
|-------|-----------------|------------|----------------------|
| val | 0.3125 | 0.3125 | 0.875 |
| holdout | **0.375** | **0.375** | **1.0** |

vs prior expanded closed-vocab holdout structure **0.0**.

## Safety
BEST morph19 unchanged; OBSERVED hold; envelope morphs exhausted.

## Next
Improve role unbind under this pointer recipe.
