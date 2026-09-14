# Spec 007 — status after family representation probe

**Authority:** Spec 007 only. `name_gate` stays false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 pin — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Plan → execute

1. **OBSERVED `partial_slot_miss`:** confirmed **hold** (no invented gold).
2. **Family gold expansion:** blocked — 356/356 already human-reviewed; no leftover reviewed rows.
3. **Executed:** frozen-structure family representation climb
   MLP(CLS||mean-pool) + class-balanced CE from famsel
   (`~/hlx-private/p1-structure-unbind-famrepr-20260914/`).

## Result

| run | structure | role | pointer | family |
|-----|-----------|------|---------|--------|
| **famsel (keep)** | **1.0** | **1.0** | **1.0** | **≈0.676** |
| famhead (reject) | 1.0 | 1.0 | 1.0 | ≈0.676 |
| famrepr (reject) | 1.0 | 1.0 | 1.0 | ≈0.649 |

- Structure/role/pointer held under freeze.
- Family holdout **missed majority**; val-only lift did not generalize.
- `promotion.keep=false`; BEST unchanged.

## Working joint

`~/hlx-private/p1-structure-unbind-famsel-20260914/`

## Next (stop thrashing)

1. **OBSERVED:** remain **hold** until explicit operator policy change.
2. **Family:** needs **new human-reviewed family gold** (rebalance beyond ai-native majority) before another train climb.
3. **No BEST overwrite.** Envelope-only morphs stay exhausted.
4. Do **not** re-run family-CE / family-repr climbs on the same gold.
