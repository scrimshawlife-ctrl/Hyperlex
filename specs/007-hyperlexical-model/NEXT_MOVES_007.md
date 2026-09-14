# Spec 007 — famcls22 KEEP (last-N=6); accept15 data pin

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins

| pin | path | note |
|-----|------|------|
| **weight joint (family-line)** | `~/hlx-private/p1-structure-unbind-famcls22-20260914/` | **KEEP**; last-N=6 encoder on accept15 |
| **data pin** | `~/hlx-private/p1-classify-accept15-20260914/prepare` | residual-miss after famcls21 |
| prior keep (init) | `~/hlx-private/p1-structure-unbind-famcls21-20260914/` | last-N=6 ancestry |
| structure reference | `~/hlx-private/p1-structure-unbind-famsel-20260914/` | prior structure-line keep |

## This pass

1. Merged famcls21 KEEP on accept14 (family 0.800).
2. Confusion dump → accept15 residual-miss gold (+79 promoted).
3. Fair famcls21 on accept15-test: family **0.8169**, structure/role/pointer **1.0**.
4. **famcls22** same last-N=6 recipe, init famcls21:

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls21 baseline | 1.0 | 1.0 | 1.0 | 0.817 |
| **famcls22 (N=6)** | **1.0** | **1.0** | **1.0** | **0.831** |

Pre-registered gate PASSED (family Δ +0.014; absolute structure hold).

## Policy

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. Prefer recipe changes when same-N climbs plateau
4. Agent may still classify; do not invent OBSERVED structure gold

## Next

1. Confusion dump of famcls22 on accept15-test for remaining misses
2. accept16 residual-miss gold + fair famcls22 baseline + famcls23 climb
3. Hold envelope morphs / BEST overwrite until ladder 0.55 has a real plan
