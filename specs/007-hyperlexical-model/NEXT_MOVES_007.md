# Spec 007 — merged status (famsel keep)

**Authority:** Spec 007 only. `name_gate` stays false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 pin — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Merge

Operator **ok merge**. Structure line closed on the **famsel** joint:

`~/hlx-private/p1-structure-unbind-famsel-20260914/`

| metric | holdout |
|--------|---------|
| structure_exact | **1.0** |
| role_exact | **1.0** |
| filler_pointer_exact | **1.0** |
| family_exact | ≈0.676 (majority baseline) |

Rejected / not merged: ptrbal, famclimb, famhead, famrepr.

## Policy locks

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. No more family CE/repr climbs on current gold without new human-reviewed family labels

## Next (blocked on humans)

- New reviewed family gold (rebalance past ai-native majority), **or**
- Explicit OBSERVED policy change
