# Spec 007 — famcls18 KEEP (last-N=4); accept12 data pin

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins

| pin | path | note |
|-----|------|------|
| **weight joint (family-line)** | `~/hlx-private/p1-structure-unbind-famcls18-20260914/` | **KEEP**; last-N=4 encoder on accept12 |
| **data pin** | `~/hlx-private/p1-classify-accept12-20260914/prepare` | residual-miss after famcls17 |
| prior keep (init) | `~/hlx-private/p1-structure-unbind-famcls17-20260914/` | last-N=4 ancestry |
| structure reference | `~/hlx-private/p1-structure-unbind-famsel-20260914/` | prior structure-line keep |

## This pass

1. famcls17 KEEP on accept11 (family 0.713).
2. Confusion dump → accept12 novel residual-miss gold (+315 promoted).
3. Fair famcls17 on accept12-test: family **0.7170**, structure/role/pointer **1.0**.
4. **famcls18** same recipe (last-N=4, enc LR 1e-5), init famcls17:

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls17 baseline | 1.0 | 1.0 | 1.0 | 0.717 |
| **famcls18 (N=4)** | **1.0** | **1.0** | **1.0** | **0.774** |

Pre-registered gate PASSED (family Δ +0.057; absolute structure hold).

## Policy

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. Prefer recipe changes when same-N climbs plateau
4. Agent may still classify; do not invent OBSERVED structure gold

## Next

1. Confusion dump of famcls18 on accept12-test for remaining misses
2. accept13 residual-miss gold + fair famcls18 baseline + famcls19 climb
3. Hold envelope morphs / BEST overwrite until ladder 0.55 has a real plan
