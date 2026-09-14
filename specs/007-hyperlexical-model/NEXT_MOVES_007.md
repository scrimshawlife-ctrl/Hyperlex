# Spec 007 — pass-2 labels in; famcls5 rejected; hard pause

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins

| pin | path | note |
|-----|------|------|
| **weight joint** | `~/hlx-private/p1-structure-unbind-famcls-20260914/` | structure/role/pointer **1.0** |
| **data pin** | `~/hlx-private/p1-classify-accept2-20260914/prepare` | accept + pass-2 kinship/gaming (+15) |
| structure reference | `~/hlx-private/p1-structure-unbind-famsel-20260914/` | prior structure-line keep |

Accept2-test famcls baseline family **≈0.644** (structure 1.0).

## Pass-2 label decisions

**Accepted:** kinship `fam, homie, bestie, yo unc, big bro, big sis, big unc, lil bro`; gaming `gg ez, debuff, diffed, feeder, inting, ez clap, feeding`.

**Rejected:** all pass-2 `none` (joke euphemisms, not non-slang controls); gaming `point`.

## Rejected resumes

| run | fair family vs baseline | structure |
|-----|-------------------------|-----------|
| famcls2 | — | regress |
| famcls3 | 0.636 < 0.659 | hold |
| famcls4 | 0.591 < 0.659 | hold |
| **famcls5** | **0.622 < 0.644** | hold |

## Policy

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. **Hard pause** on CE/sampler/head climbs — current gold exhausted for family gains
4. Next progress needs **true non-slang `none` controls** or other high-quality reviewed labels from outside the joke-slang dump

## Next (operator)

1. Supply real `none`/control surfaces (or other reviewed family gold)
2. Only then rebuild prepare and resume with gate family > accept2 baseline + structure hold
3. Hold envelope morphs / BEST overwrite
