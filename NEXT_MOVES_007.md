# Spec 007 — famcls16 KEEP (last-N=4); accept10 data pin

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins

| pin | path | note |
|-----|------|------|
| **weight joint (family-line)** | `~/hlx-private/p1-structure-unbind-famcls16-20260914/` | **KEEP**; last-N=4 encoder on accept10 |
| **data pin** | `~/hlx-private/p1-classify-accept10-20260914/prepare` | residual-miss after famcls15 |
| prior keep (init) | `~/hlx-private/p1-structure-unbind-famcls15-20260914/` | last-N=4 ancestry |
| structure reference | `~/hlx-private/p1-structure-unbind-famsel-20260914/` | prior structure-line keep |

## This pass

1. accept10 built from famcls15 accept9-test residual misses (+94 promoted).
2. Fair famcls15 on accept10-test: family **0.6628**, structure/role/pointer **1.0**.
3. **famcls16** same recipe (last-N=4, enc LR 1e-5), init famcls15:

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls15 baseline | 1.0 | 1.0 | 1.0 | 0.663 |
| **famcls16 (N=4)** | **1.0** | **1.0** | **1.0** | **0.686** |

Pre-registered gate PASSED (family Δ +0.023; absolute structure hold).

## Policy

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. Prefer recipe changes when same-N climbs plateau
4. Agent may still classify; do not invent OBSERVED structure gold

## Next

1. Confusion dump of famcls16 on accept10-test (done in-session) → accept11 residual-miss gold
2. Fair famcls16 on accept11 + famcls17 climb (in flight)
3. Hold envelope morphs / BEST overwrite until ladder 0.55 has a real plan
