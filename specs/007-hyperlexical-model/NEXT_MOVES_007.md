# Spec 007 — after famcls merge + famcls2 reject

**Authority:** Spec 007 only. `name_gate` stays false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 pin — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## MERGED working joints

| line | path | holdout |
|------|------|---------|
| structure reference | `~/hlx-private/p1-structure-unbind-famsel-20260914/` | structure/role/pointer **1.0**; family ≈0.676 on prior test |
| **family-resume MERGED** | `~/hlx-private/p1-structure-unbind-famcls-20260914/` | structure/role/pointer **1.0**; family **≈0.690** vs new-test majority ≈0.595 |

Classify expand prepare (`p1-classify-expand-20260914/`) remains the family-resume data pin.

## Rejected this turn

**famcls2** (`p1-structure-unbind-famcls2-20260914/`): class-balance + floor 0.60.

| metric | famcls | famcls2 |
|--------|--------|---------|
| structure | **1.0** | 0.958 |
| pointer | **1.0** | 0.958 |
| family | 0.690 | 0.786 |

Rejected: structure/pointer regression. Val family never cleared floor (max 0.55).

## Policy locks

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. Do not train INFERRED until explicit review accept
4. No invented OBSERVED structure gold
5. No further CE/sampler climbs on current gold without new reviewed labels

## Next

1. **Operator review** of `p1-classify-expand-20260914/review_queue_*.jsonl` (pass shortlist n≈19 + golden terms n≈12; `none` still empty)
2. Promote only explicitly accepted labels into prepare, then resume
3. Hold envelope-only morphs / BEST overwrite
