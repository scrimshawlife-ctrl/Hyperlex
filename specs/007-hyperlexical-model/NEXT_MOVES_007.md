# Spec 007 — status after frozen family-head probe

**Authority:** Spec 007 only. `name_gate` stays false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 pin — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Plan → execute

1. **Fact:** famsel family holdout ≈0.676 == majority baseline (ai-native 25/37).
2. **Prior reject:** joint family-CE×N (structure regressed; family flat).
3. **Executed:** structure-frozen class-balanced family-head finetune from famsel
   (`~/hlx-private/p1-structure-unbind-famhead-20260914/`).

## Result

| run | structure | role | pointer | family |
|-----|-----------|------|---------|--------|
| **famsel (keep)** | **1.0** | **1.0** | **1.0** | **≈0.676** |
| famhead (reject) | 1.0 | 1.0 | 1.0 | ≈0.676 |

- Structure/role/pointer held under freeze.
- Family holdout did **not** beat majority; val-only lift (≈0.714) failed to generalize.
- `promotion.keep=false`; BEST unchanged; OBSERVED still hold.

## Working joint

`~/hlx-private/p1-structure-unbind-famsel-20260914/`

## Next (do not thrash)

1. **OBSERVED `partial_slot_miss`:** policy remains **hold** (no invented gold).
2. **Family:** needs new reviewed family gold and/or a representation change — not more family-head CE or joint CE upweight.
3. **BEST / envelope morphs:** no overwrite; envelope-only morphs stay exhausted.
