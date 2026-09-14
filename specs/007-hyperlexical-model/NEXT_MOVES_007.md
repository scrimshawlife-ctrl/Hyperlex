# Spec 007 — status after classify expand + famcls keep

**Authority:** Spec 007 only. `name_gate` stays false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 pin — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Working joints

| line | path | holdout |
|------|------|---------|
| structure reference | `~/hlx-private/p1-structure-unbind-famsel-20260914/` | structure/role/pointer **1.0**; family ≈0.676 on prior test |
| **family-resume keep** | `~/hlx-private/p1-structure-unbind-famcls-20260914/` | structure/role/pointer **1.0**; family **≈0.690** vs new-test majority ≈0.595 |

## Done this turn

1. **Classify expand** (`p1-classify-expand-20260914/`): +33 OBSERVED family surfaces (brainrot/kinship/gaming). `none` still empty. INFERRED/golden terms parked for review.
2. **famcls resume train** from famsel init on expand prepare — holdout family beats new majority; structure holds. BEST unchanged.
3. Docs receipt pushed to Hyperlex main.

## Policy locks

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. Do not train INFERRED until operator review
4. No invented OBSERVED structure gold

## Next

1. Operator review of INFERRED / golden-term queues (especially `none`)
2. Optional sampler / floor tweak if val family stays under floor
3. Hold further CE/repr climbs without new reviewed labels
