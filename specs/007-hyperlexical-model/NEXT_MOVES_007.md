# Spec 007 — famcls25 KEEP (last-N=8); accept17 data pin

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins

| pin | path | note |
|-----|------|------|
| **weight joint (family-line)** | `~/hlx-private/p1-structure-unbind-famcls25-20260914/` | **KEEP**; last-N=8 encoder on accept17 |
| **data pin** | `~/hlx-private/p1-classify-accept17-20260914/prepare` | residual-miss after famcls23 |
| prior keep (init) | `~/hlx-private/p1-structure-unbind-famcls23-20260914/` | last-N=6 ancestry |
| reject (do not init) | `~/hlx-private/p1-structure-unbind-famcls24-20260914/` | N=6 plateau + structure slip |

## This pass

1. Merged famcls23 KEEP on accept16 (family 0.853).
2. Confusion dump → accept17 residual-miss gold (+261 promoted).
3. Fair famcls23 on accept17-test: family **0.8608**, structure/role/pointer **1.0**.
4. **famcls24** last-N=6, full 40 ep → **REJECT** (family tie; structure/pointer 0.958).
5. Protocol deepen **N=6→8**; **famcls25** full 40 ep → **KEEP**:

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls23 baseline | 1.0 | 1.0 | 1.0 | 0.861 |
| famcls24 (N=6) | 0.958 | 1.0 | 0.958 | 0.861 |
| **famcls25 (N=8)** | **1.0** | **1.0** | **1.0** | **0.930** |

## Policy

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. Prefer recipe changes when same-N climbs plateau (deepen N)
4. Agent may still classify; do not invent OBSERVED structure gold
5. Training runs must complete all 40 epochs

## Next

1. Confusion dump of famcls25 on accept17-test for remaining misses
2. accept18 residual-miss gold + fair famcls25 baseline + famcls26 climb (full 40 ep)
3. Hold envelope morphs / BEST overwrite until ladder 0.55 has a real plan
