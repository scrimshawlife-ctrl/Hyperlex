# Spec 007 — after accept-recommended + famcls3 reject

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins

| pin | path | note |
|-----|------|------|
| weight joint | `~/hlx-private/p1-structure-unbind-famcls-20260914/` | structure/role/pointer **1.0**; family ≈0.690 expand-test / **0.659** accept-test |
| **data pin** | `~/hlx-private/p1-classify-accept-20260914/prepare` | +18 operator-accepted labels |
| structure reference | `~/hlx-private/p1-structure-unbind-famsel-20260914/` | prior structure-line keep |

## Rejected

- **famcls2**: structure/pointer regress
- **famcls3**: fair accept-test family 0.636 < famcls 0.659 (structure tied at 1.0)

## Policy locks

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. No wholesale INFERRED train
4. No CE/sampler thrash without new reviewed labels or a clear recipe hypothesis

## Next

1. Optional short resume on accept prepare that must beat famcls **0.659** family on accept-test with structure hold
2. Or more operator labels for `none` / weak families
3. Hold envelope morphs / BEST overwrite
