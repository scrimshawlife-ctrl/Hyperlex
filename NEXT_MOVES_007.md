# Spec 007 — famcls19 KEEP (last-N=4); accept13 data pin

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins

| pin | path | note |
|-----|------|------|
| **weight joint (family-line)** | `~/hlx-private/p1-structure-unbind-famcls19-20260914/` | **KEEP**; last-N=4 encoder on accept13 |
| **data pin** | `~/hlx-private/p1-classify-accept13-20260914/prepare` | residual-miss after famcls18 |
| prior keep (init) | `~/hlx-private/p1-structure-unbind-famcls18-20260914/` | last-N=4 ancestry |
| structure reference | `~/hlx-private/p1-structure-unbind-famsel-20260914/` | prior structure-line keep |

## This pass

1. Merged famcls18 KEEP on accept12 (family 0.774).
2. Confusion dump → accept13 residual-miss gold (+161 promoted).
3. Fair famcls18 on accept13-test: family **0.7712**, structure/role/pointer **1.0**.
4. **famcls19** same recipe (last-N=4, enc LR 1e-5), init famcls18:

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls18 baseline | 1.0 | 1.0 | 1.0 | 0.771 |
| **famcls19 (N=4)** | **1.0** | **1.0** | **1.0** | **0.805** |

Pre-registered gate PASSED (family Δ +0.034; absolute structure hold).

## Policy

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. Prefer recipe changes when same-N climbs plateau
4. Agent may still classify; do not invent OBSERVED structure gold

## Next

1. Confusion dump of famcls19 on accept13-test for remaining misses
2. accept14 residual-miss gold + fair famcls19 baseline + famcls20 climb
3. Hold envelope morphs / BEST overwrite until ladder 0.55 has a real plan
