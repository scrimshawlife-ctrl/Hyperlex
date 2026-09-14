# Receipt — family climb under structure floor (2026-09-14)

SHADOW / `name_gate=false`. No Hub. No BEST overwrite.

## Action
Operator **continue**: family climb under structure-floor selection.

- family CE×3; role/pointer CE×1.5; scheme_embed kept
- structure_floor=0.75; family_floor=0.5; 24 ep; seed 35
- selection=`family_max_under_structure_floor`; best_epoch=22
- Out: `~/hlx-private/p1-structure-unbind-famclimb-20260914/out`

## Metrics
| split | structure | role | pointer | family |
|-------|-----------|------|---------|--------|
| val | 0.875 | 1.0 | 0.875 | ≈0.686 |
| holdout | ≈0.833 | 1.0 | ≈0.833 | ≈0.676 |

## Verdict
**Reject.** Keep famsel (holdout structure/role/pointer=1.0, family≈0.676).

## Safety
BEST morph19 unchanged; OBSERVED hold.

## Next
OBSERVED policy hold; no BEST overwrite; avoid more family-CE-only climbs.
