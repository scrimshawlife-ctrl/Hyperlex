# Spec 007 — famcls23 KEEP (last-N=6); accept16 data pin

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins

| pin | path | note |
|-----|------|------|
| **weight joint (family-line)** | `~/hlx-private/p1-structure-unbind-famcls23-20260914/` | **KEEP**; last-N=6 encoder on accept16 |
| **data pin** | `~/hlx-private/p1-classify-accept16-20260914/prepare` | residual-miss after famcls22 |
| prior keep (init) | `~/hlx-private/p1-structure-unbind-famcls22-20260914/` | last-N=6 ancestry |
| structure reference | `~/hlx-private/p1-structure-unbind-famsel-20260914/` | prior structure-line keep |

## This pass

1. Merged famcls22 KEEP on accept15 (family 0.831).
2. Confusion dump → accept16 residual-miss gold (+70 promoted).
3. Fair famcls22 on accept16-test: family **0.8400**, structure/role/pointer **1.0**.
4. **famcls23** same last-N=6 recipe, init famcls22:

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls22 baseline | 1.0 | 1.0 | 1.0 | 0.840 |
| **famcls23 (N=6)** | **1.0** | **1.0** | **1.0** | **0.853** |

Pre-registered gate PASSED (family Δ +0.013; absolute structure hold).

## Policy

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. Prefer recipe changes when same-N climbs plateau
4. Agent may still classify; do not invent OBSERVED structure gold

## Next

1. Confusion dump of famcls23 on accept16-test for remaining misses
2. accept17 residual-miss gold + fair famcls23 baseline + famcls24 climb
3. Hold envelope morphs / BEST overwrite until ladder 0.55 has a real plan
