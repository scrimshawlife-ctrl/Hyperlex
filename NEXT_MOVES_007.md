# Spec 007 — accept8 MERGED; famcls13 KEEP (last-N encoder)

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins

| pin | path | note |
|-----|------|------|
| **weight joint (family-line)** | `~/hlx-private/p1-structure-unbind-famcls13-20260914/` | **KEEP**; last-N encoder + family head on accept8 |
| **data pin** | `~/hlx-private/p1-classify-accept8-20260914/prepare` | **MERGED** miss-targeted contrastive gold (+192) |
| prior keep (init) | `~/hlx-private/p1-structure-unbind-famcls12-20260914/` | previous family-line keep |
| structure reference | `~/hlx-private/p1-structure-unbind-famsel-20260914/` | prior structure-line keep |

## This pass

1. Merged famcls12 KEEP; continued from its accept7-test dump (30 misses).
2. **accept8:** +192 miss-targeted contrastive surfaces.
3. Fair famcls12 on accept8-test: family **0.543**, structure/role/pointer **1.0**.
4. **famcls13** last-N=2 init famcls12:

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls12 baseline | 1.0 | 1.0 | 1.0 | 0.543 |
| **famcls13** | **1.0** | **1.0** | **1.0** | **0.614** |

Pre-registered gate PASSED (family Δ +0.071; absolute structure hold).

## Policy

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. Prefer structure-holding encoder-touching recipes when family stalls
4. Agent may still classify; do not invent OBSERVED structure gold

## Next

1. Confusion dump of famcls13 on accept8-test for remaining misses
2. Hold envelope morphs / BEST overwrite until ladder 0.55 has a real plan
