# Receipt — expanded dual-scheme structure gold (2026-09-14)

SHADOW / `name_gate=false`. No Hub. No BEST overwrite.

## Action
Operator **continue as recommended** after holdout miss: expand structure gold.

- Annotated: 33 → **62** multitoken bases (`~/hlx-private/p1-structure-annotated-expanded-20260914/`)
- Intake: 62/62 promoted (`~/hlx-private/p1-structure-intake-expanded-20260914/`)
- Dual prepare + 12-base holdout: `~/hlx-private/p1-structure-dual-expanded-prepare-20260914/`
- Train 12 epochs → `~/hlx-private/p1-structure-dual-expanded-20260914/out`

## Metrics
| split | structure_exact | family_exact |
|-------|-----------------|--------------|
| val | 0.125 (n=16) | ≈0.686 (n=35) |
| holdout | **0.0 (n=24)** | ≈0.676 (n=37) |

More of the same positional recipe did not fix holdout generalization.

## Safety
BEST morph19 unchanged; OBSERVED still hold; envelope morphs exhausted.

## Next
Change structure recipe — not another gold dump or epoch climb on whitespace `pos_i`.
