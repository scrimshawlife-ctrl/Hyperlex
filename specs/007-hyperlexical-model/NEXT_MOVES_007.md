# Spec 007 — accept3 labels in; famcls6 rejected; pause on thrash

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins

| pin | path | note |
|-----|------|------|
| **weight joint** | `~/hlx-private/p1-structure-unbind-famcls-20260914/` | structure/role/pointer **1.0** |
| **data pin** | `~/hlx-private/p1-classify-accept3-20260914/prepare` | accept2 + **+115** agent labels |
| structure reference | `~/hlx-private/p1-structure-unbind-famsel-20260914/` | prior structure-line keep |

Accept3-test famcls baseline family **≈0.612** (structure 1.0).

## Agent classification (unlocked)

Operator: agent may handle all classification jobs.

**Accepted:** clean kinship/gaming lexicon from inferred queue + remaining inferred_pass (`agentic slop`, `token burn`, `hallucination`, `revenge bet`, `sharp money`, `organic velocity`, `copemaxxing`).

**Rejected:** all inferred `none` (still joke slang); wiki/declension/prose; weak pass items (`tokens`, `middle`, joke idioms).

## Rejected resumes

| run | fair family vs baseline | structure |
|-----|-------------------------|-----------|
| famcls2–5 | prior rejects | see prior receipts |
| **famcls6** | **0.633 > 0.612** | **0.875 (FAIL hold)** |

## Policy

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. Pause CE/sampler/head climbs — need better gold (esp. true `none` controls), not more thrash
4. Agent may keep classifying when new queues appear; do not invent OBSERVED structure gold

## Next

1. Supply real non-slang `none`/control surfaces (or other reviewed minority gold)
2. Only then rebuild prepare and resume with gate family > accept3 baseline **and** structure/role/pointer hold at 1.0
3. Hold envelope morphs / BEST overwrite
