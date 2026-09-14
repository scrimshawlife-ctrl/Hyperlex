# Receipt — dual-scheme structure holdout probe (2026-09-14)

SHADOW / `name_gate=false`. No Hub. No BEST overwrite.

## Action
Operator **continue** after dual climb plateau: structure holdout probe.

- Prepare: `~/hlx-private/p1-structure-dual-holdout-prepare-20260914/`
  - Moved **6 train structure bases** (12 dual rows = positional + type_slot; seed=7) to `split=test`
  - Structure train 38 / val 16 / test 12; family test 31
- Train: Dual ModernBERT 12 epochs → **new** `~/hlx-private/p1-structure-dual-holdout-20260914/out`

## Metrics
| split | structure_exact | family_exact |
|-------|-----------------|--------------|
| val | 0.625 (n=16) | ≈0.737 (n=38) |
| **holdout test** | **0.0 (n=12)** | ≈0.742 (n=31) |

Val plateau **does not** generalize to held-out structure bases.

## Safety
- `best_overwrite=false`; `best_unchanged=true`; BEST morph19 path+mtime unchanged
- OBSERVED `partial_slot_miss` still hold; envelope morphs exhausted

## Next
Expand structure gold or change structure recipe — **not** another epoch climb on these 33 bases.
