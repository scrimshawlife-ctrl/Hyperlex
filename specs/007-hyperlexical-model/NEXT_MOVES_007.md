# Spec 007 — famcls21 KEEP (last-N=6); accept14 data pin

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins

| pin | path | note |
|-----|------|------|
| **weight joint (family-line)** | `~/hlx-private/p1-structure-unbind-famcls21-20260914/` | **KEEP**; last-N=6 encoder on accept14 |
| **data pin** | `~/hlx-private/p1-classify-accept14-20260914/prepare` | residual-miss after famcls19 |
| prior keep (init) | `~/hlx-private/p1-structure-unbind-famcls19-20260914/` | last-N=4 ancestry |
| rejected | `~/hlx-private/p1-structure-unbind-famcls20-20260914/` | last-N=4 clone on accept14 |
| structure reference | `~/hlx-private/p1-structure-unbind-famsel-20260914/` | prior structure-line keep |

## This pass

1. Merged famcls19 KEEP on accept13 (family 0.805).
2. Confusion dump → accept14 residual-miss gold (+188 promoted).
3. Fair famcls19 on accept14-test: family **0.7846**, structure/role/pointer **1.0**.
4. **famcls20** same last-N=4 recipe → **REJECT** (family 0.7769 < 0.7846).
5. **famcls21** new recipe last-N=**6**, init famcls19:

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls19 baseline | 1.0 | 1.0 | 1.0 | 0.785 |
| famcls20 (N=4) | 1.0 | 1.0 | 1.0 | 0.777 |
| **famcls21 (N=6)** | **1.0** | **1.0** | **1.0** | **0.800** |

Pre-registered gate PASSED (family Δ +0.015; absolute structure hold).

## Policy

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. Prefer recipe changes when same-N climbs plateau — applied (N=4 reject → N=6 keep)
4. Agent may still classify; do not invent OBSERVED structure gold

## Next

1. Confusion dump of famcls21 on accept14-test for remaining misses
2. accept15 residual-miss gold + fair famcls21 baseline + famcls22 climb
3. Hold envelope morphs / BEST overwrite until ladder 0.55 has a real plan
