# Receipt — family-aware selection climb (2026-09-14)

SHADOW / `name_gate=false`. No Hub. No BEST overwrite.

## Action
Operator **continue** after ptrbal: family-aware selection under balanced scheme unbind.

- role/pointer CE×1.5; scheme_embed kept; family_floor=0.5
- 24 ep; seed 28; selection=`family_floor_then_structure`; best_epoch=1
- Prepare reused: `~/hlx-private/p1-structure-dual-expanded-prepare-20260914/`
- Out: `~/hlx-private/p1-structure-unbind-famsel-20260914/out`

## Metrics
| split | structure_exact | role_exact | filler_pointer_exact | family_exact |
|-------|-----------------|------------|----------------------|--------------|
| val | 0.75 | 1.0 | 0.75 | ≈0.629 |
| holdout | **1.0** | **1.0** | **1.0** | ≈0.676 |

## Verdict
Joint promotion over scheme; keep this out as working checkpoint.

## Safety
BEST morph19 unchanged; OBSERVED hold; envelope morphs exhausted.

## Next
OBSERVED policy hold; optional family climb without structure regression; no BEST overwrite.
