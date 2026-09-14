# Spec 007 — famcls17 KEEP (last-N=4); accept11 data pin

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins

| pin | path | note |
|-----|------|------|
| **weight joint (family-line)** | `~/hlx-private/p1-structure-unbind-famcls17-20260914/` | **KEEP**; last-N=4 encoder on accept11 |
| **data pin** | `~/hlx-private/p1-classify-accept11-20260914/prepare` | residual-miss after famcls16 |
| prior keep (init) | `~/hlx-private/p1-structure-unbind-famcls16-20260914/` | last-N=4 ancestry |
| structure reference | `~/hlx-private/p1-structure-unbind-famsel-20260914/` | prior structure-line keep |

## This pass

1. famcls16 KEEP on accept10 (family 0.686).
2. Confusion dump → accept11 residual-miss gold (+225 promoted).
3. Fair famcls16 on accept11-test: family **0.6809**, structure/role/pointer **1.0**.
4. **famcls17** same recipe (last-N=4, enc LR 1e-5), init famcls16:

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls16 baseline | 1.0 | 1.0 | 1.0 | 0.681 |
| **famcls17 (N=4)** | **1.0** | **1.0** | **1.0** | **0.713** |

Pre-registered gate PASSED (family Δ +0.032; absolute structure hold).

## Policy

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. Prefer recipe changes when same-N climbs plateau
4. Agent may still classify; do not invent OBSERVED structure gold

## Next

1. Confusion dump of famcls17 on accept11-test for remaining misses
2. accept12 residual-miss gold + fair famcls17 baseline + famcls18 climb
3. Hold envelope morphs / BEST overwrite until ladder 0.55 has a real plan
