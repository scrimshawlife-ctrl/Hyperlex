# Spec 007 — accept4 labels in; famcls7 rejected; hard pause on joint thrash

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins

| pin | path | note |
|-----|------|------|
| **weight joint** | `~/hlx-private/p1-structure-unbind-famcls-20260914/` | structure/role/pointer **1.0** |
| **data pin** | `~/hlx-private/p1-classify-accept4-20260914/prepare` | accept3 + **+131** agent labels (21 gaming salvage, **110 none**) |
| structure reference | `~/hlx-private/p1-structure-unbind-famsel-20260914/` | prior structure-line keep |

Accept4-test famcls baseline family **≈0.545** (structure 1.0). Drop vs accept3 baseline is expected: new `none` class unseen by famcls.

## Agent classification (unlocked)

Operator: agent may handle all classification jobs.

### accept3 (prior)
+115 kinship/gaming lexicon + inferred_pass.

### accept4 (this pass)
- **Salvaged** 21 clean gaming-meta lexicon over-rejected in accept3
- **Seeded** 110 non-slang `none` controls (everyday English; dump joke-euphemisms still rejected)

## Rejected resumes

| run | fair family vs baseline | structure |
|-----|-------------------------|-----------|
| famcls2–5 | prior rejects | see prior receipts |
| famcls6 (accept3) | 0.633 > 0.612 | 0.875 FAIL |
| **famcls7 (accept4)** | **0.618 > 0.545** | **0.917 FAIL** |

Pattern: joint CE resumes buy family points by spending structure/pointer hold.

## Policy

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. **Hard pause** on joint CE/sampler/head climbs that do not preserve structure 1.0
4. Agent may keep classifying new queues; do not invent OBSERVED structure gold
5. Next weight work needs a structure-preserving recipe (or new reviewed structure gold), not another famclsN on the same joint recipe

## Next

1. If continuing weight work: freeze structure trunk / use family-head-only with structure regression abort — only if pre-registered and structure hold is mandatory
2. Prefer new reviewed structure gold over more family CE thrash
3. Hold envelope morphs / BEST overwrite
