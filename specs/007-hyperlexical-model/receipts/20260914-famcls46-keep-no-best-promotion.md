# Receipt — famcls46 Climb KEEP (no BEST promotion)

## Gate result (accept24-test)
Init famcls45 · accept24 · N=8 · LR 5e-6 · aux=0.25 · upsample=8 · 40 ep (best val epoch 1).

| gate | result |
|------|--------|
| family > 0.9545454545454546 | **0.9899** PASS |
| structure = 1.0 | **1.0** |
| role = 1.0 | **1.0** |
| pointer = 1.0 | **1.0** |

SMOKE `promotion.keep=true`. Climb weight pin: `~/hlx-private/p1-structure-unbind-famcls46-20260914/`.

## Explicit non-promotion
- Climb KEEP ≠ BEST promotion.
- **BEST remains morph19** (`~/.hyperlex/models/BEST` → morph19; `model.safetensors` mtime 2026-09-12 unchanged).
- SMOKE: `best_unchanged=true`, `best_overwrite=false`, `name_gate=false`.
- Val best_val_score `[0.9082, 0.8125, 1.0, 0.8125]` — does not clear morph19 civilian `unbind_exact≈0.4545`.
- Candidate-only draft on Spark: `p1-structure-unbind-famcls46-20260914/PROMOTION_RECEIPT.md` (**DO NOT PROMOTE**).

## Context
- famcls45 preserved at `~/hlx-private/preserved/famcls45-20260914/` (originals intact).
- Sibling may continue accept25 / further climb — do not clear GPUs while sibling work is active.
- 43 vs 44 holdout comparison: `receipts/20260914-famcls43-vs-44-accept23-holdout.md`.
