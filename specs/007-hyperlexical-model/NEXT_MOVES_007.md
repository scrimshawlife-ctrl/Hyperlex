# Spec 007 — accept7 MERGED; famcls12 KEEP (last-N encoder)

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins

| pin | path | note |
|-----|------|------|
| **weight joint (family-line)** | `~/hlx-private/p1-structure-unbind-famcls12-20260914/` | **KEEP**; last-N encoder + family head on accept7 |
| **data pin** | `~/hlx-private/p1-classify-accept7-20260914/prepare` | **MERGED** adversarial contrastive gold |
| prior keep (init) | `~/hlx-private/p1-structure-unbind-famcls9-20260914/` | freeze ancestry |
| structure reference | `~/hlx-private/p1-structure-unbind-famsel-20260914/` | prior structure-line keep |

## This pass

1. Merged accept7 as official data pin (post famcls10/11 head-only REJECT).
2. **famcls12** recommended unlock: last N=2 encoder layers + family head; structure heads frozen.

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls9 baseline | 1.0 | 1.0 | 1.0 | 0.452 |
| **famcls12** | **1.0** | **1.0** | **1.0** | **0.516** |

Pre-registered gate PASSED (family Δ +0.065; absolute structure hold).

## Rejected context

famcls10 inv-freq CE head-only and famcls11 hard-neg head-only both missed the fair gate.

## Policy

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. Prefer structure-holding encoder-touching recipes when family stalls
4. Agent may still classify; do not invent OBSERVED structure gold

## Next

1. Confusion dump of famcls12 on accept7-test for remaining misses
2. Hold envelope morphs / BEST overwrite until ladder 0.55 has a real plan
