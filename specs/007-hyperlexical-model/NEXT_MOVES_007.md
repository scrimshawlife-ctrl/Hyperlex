# Spec 007 — famcls15 KEEP (last-N=4); accept9 data pin

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins

| pin | path | note |
|-----|------|------|
| **weight joint (family-line)** | `~/hlx-private/p1-structure-unbind-famcls15-20260914/` | **KEEP**; last-N=4 encoder on accept9 |
| **data pin** | `~/hlx-private/p1-classify-accept9-20260914/prepare` | residual-miss contrastive gold |
| prior keep (init) | `~/hlx-private/p1-structure-unbind-famcls13-20260914/` | last-N=2 ancestry |
| structure reference | `~/hlx-private/p1-structure-unbind-famsel-20260914/` | prior structure-line keep |

## This pass

1. famcls14 last-N=2 on accept9 **REJECTED** (family tied 0.615).
2. **famcls15** new recipe: last-N=**4**, encoder LR **1e-5**, init famcls13:

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls13 baseline | 1.0 | 1.0 | 1.0 | 0.615 |
| famcls14 (N=2) | 1.0 | 1.0 | 1.0 | 0.615 |
| **famcls15 (N=4)** | **1.0** | **1.0** | **1.0** | **0.641** |

Pre-registered gate PASSED (family Δ +0.026; absolute structure hold).

## Policy

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. Prefer recipe changes when same-N climbs plateau
4. Agent may still classify; do not invent OBSERVED structure gold

## Next

1. Confusion dump of famcls15 on accept9-test for remaining misses
2. Hold envelope morphs / BEST overwrite until ladder 0.55 has a real plan
