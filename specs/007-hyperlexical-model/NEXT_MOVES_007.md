# Spec 007 — status after classify expand (resume training)

**Authority:** Spec 007 only. `name_gate` stays false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 pin — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Merge (prior)

Operator **ok merge**. Structure line closed on **famsel**:

`~/hlx-private/p1-structure-unbind-famsel-20260914/`

| metric | holdout |
|--------|---------|
| structure_exact | **1.0** |
| role_exact | **1.0** |
| filler_pointer_exact | **1.0** |
| family_exact | ≈0.676 (majority baseline) |

Rejected / not merged: ptrbal, famclimb, famhead, famrepr.

## Done this turn — classify expand

Unblocked family resume by promoting **OBSERVED-only** short surfaces into prepare:

- Pack: `~/hlx-private/p1-classify-expand-20260914/`
- Prepare: `…/prepare/plan.json` (status `PREPARED_NOT_RUNNABLE`)
- **+33** classify rows: brainrot-aura 11, kinship-address 13, gaming-meta 9
- Train unique after: brainrot 7 / kinship 9 / gaming 7 (`none` still 0)
- INFERRED parked for review (`review_queue_inferred.jsonl`, n≈293 after dump-`none` filter)
- Golden matched_terms parked (`review_queue_golden_terms.jsonl`) — not auto-trained

Sources: OBSERVED type_slot template projections (high_signal) + OBSERVED short surfaces (4333 dump).

## Training resume (in flight)

- Out: `~/hlx-private/p1-structure-unbind-famcls-20260914/`
- Init: famsel `out/checkpoint.pt`
- Prepare: classify-expand
- Gate: family_exact **>** ≈0.676; structure/role/pointer hold; no BEST overwrite

## Policy locks

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. Do not train on INFERRED until operator review
4. Do not invent OBSERVED structure gold

## Next

1. Finish famcls smoke; keep only if family beats majority without structure regression
2. Operator review of INFERRED / golden-term queues (especially `none`)
3. Hold further family CE/repr climbs on old gold
