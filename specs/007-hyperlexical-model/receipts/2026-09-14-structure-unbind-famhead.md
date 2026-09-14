# Receipt — frozen family-head climb (2026-09-14)

SHADOW / `name_gate=false`. No Hub. No BEST overwrite.

## Action
Plan+execute after famsel keep / famclimb reject:

- Diagnose family plateau as majority baseline (25/37 ai-native)
- Structure-frozen family-head finetune; inverse-frequency CE
- 40 ep; seed 42; init famsel; out `~/hlx-private/p1-structure-unbind-famhead-20260914/out`

## Metrics
| split | structure | role | pointer | family |
|-------|-----------|------|---------|--------|
| baseline holdout | 1.0 | 1.0 | 1.0 | ≈0.676 |
| val | 0.75 | 1.0 | 0.75 | ≈0.714 |
| holdout | **1.0** | **1.0** | **1.0** | ≈0.676 |

## Verdict
**Reject.** Keep famsel. Family head CE cannot beat majority on this gold.

## Safety
BEST morph19 unchanged; OBSERVED hold.

## Next
OBSERVED hold; no more family-CE-only climbs; family needs gold/repr change.
