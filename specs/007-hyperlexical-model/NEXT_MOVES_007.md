# Spec 007 — famcls MERGED; famcls2 floor/sampler climb next

**Authority:** Spec 007 only. `name_gate` stays false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 pin — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## MERGED (operator accepted)

| line | path | holdout |
|------|------|---------|
| structure reference | `~/hlx-private/p1-structure-unbind-famsel-20260914/` | structure/role/pointer **1.0**; family ≈0.676 on prior test |
| **family-resume MERGED** | `~/hlx-private/p1-structure-unbind-famcls-20260914/` | structure/role/pointer **1.0**; family **≈0.690** vs new-test majority ≈0.595 (Δ+0.095) |

Classify expand prepare (`p1-classify-expand-20260914/`) is the family-resume data pin. BEST untouched.

## Continue (recommended)

1. ~~Operator merge famcls~~ **done**
2. **famcls2** floor/sampler tweak in flight: class-balance family upsample + `family_floor=0.60` so val plateau (~0.625) can select high-structure epochs; init from famcls
3. INFERRED / golden-term queues remain parked for explicit label review (`none` still empty)

## Policy locks

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. Do not train INFERRED until explicit review accept
4. No invented OBSERVED structure gold
