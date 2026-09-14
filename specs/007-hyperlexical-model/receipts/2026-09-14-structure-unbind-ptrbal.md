# Receipt — pointer-rebalance climb (2026-09-14)

SHADOW / `name_gate=false`. No Hub. No BEST overwrite.

## Action
Operator **merge and continue as recommended**: pointer rebalance under scheme unbind.

- role CE×1.5, pointer CE×1.5; scheme_embed kept
- best-val by structure_exact; 24 ep; seed 21
- Prepare reused: `~/hlx-private/p1-structure-dual-expanded-prepare-20260914/`
- Out: `~/hlx-private/p1-structure-unbind-ptrbal-20260914/out`

## Metrics
| split | structure_exact | role_exact | filler_pointer_exact | family_exact |
|-------|-----------------|------------|----------------------|--------------|
| val (ep0 selected) | 0.6875 | 1.0 | 0.6875 | 0.0 |
| holdout | **0.875** | **1.0** | 0.875 | **0.0** |

vs scheme last-epoch holdout structure≈0.833 / family≈0.676.

## Verdict
Structure tick up is not a joint win — family collapsed via structure-only early-stop.
Keep scheme out as working checkpoint.

## Safety
BEST morph19 unchanged; OBSERVED hold; envelope morphs exhausted.

## Next
Family-aware selection if climbing further; OBSERVED policy hold; no BEST overwrite.
