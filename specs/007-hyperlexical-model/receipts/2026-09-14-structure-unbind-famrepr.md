# Receipt — family representation climb (2026-09-14)

SHADOW / `name_gate=false`. No Hub. No BEST overwrite.

## Action
Continue as recommended after famhead reject:

- Confirm OBSERVED hold
- Confirm no leftover reviewed family gold
- Run MLP(CLS||mean-pool) family repr under frozen structure (50 ep, seed 49)

## Metrics
| split | structure | role | pointer | family |
|-------|-----------|------|---------|--------|
| val | 0.75 | 1.0 | 0.75 | ≈0.800 |
| holdout | **1.0** | **1.0** | **1.0** | ≈0.649 |

majority baseline ≈0.676; family did not beat it.

## Verdict
**Reject.** Keep famsel. No further family CE/repr climbs without new reviewed gold.

## Safety
BEST morph19 unchanged; OBSERVED hold.

## Next
Human-reviewed family gold rebalance; OBSERVED hold; no BEST overwrite.
