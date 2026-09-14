# Spec 007 — famcls29 REJECT; famcls30 mid-LR climb in flight

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins

| pin | path | note |
|-----|------|------|
| **weight joint (family-line)** | `~/hlx-private/p1-structure-unbind-famcls25-20260914/` | last KEEP; last-N=8 on accept17 |
| **data pin** | `~/hlx-private/p1-classify-accept19-20260914/prepare` | residual after deepen fail |
| reject (do not init) | famcls24,26,27,28,29 | see receipts |
| **BEST** | morph19 | untouched |

## Recent gates

| run | recipe | data | fair baseline | family | structure | verdict |
|-----|--------|------|---------------|--------|-----------|---------|
| famcls25 | N=8, init famcls23 | accept17 | 0.8608 | **0.9304** | 1.0 | **KEEP** |
| famcls26 | N=8, init famcls25 | accept18 | 0.9337 | 0.9277 | 1.0 | REJECT |
| famcls27 | N=10, init famcls25 | accept18 | 0.9337 | 0.8434 | 1.0 | REJECT |
| famcls28 | N=8 LR 1e-5, init famcls25 | accept19 | 0.9368 | **0.9598** | **0.958** | REJECT |
| famcls29 | N=8 LR 5e-6, init famcls25 | accept19 | 0.9368 | **0.9195** | 1.0 | REJECT |
| famcls30 | N=8 LR **7.5e-6**, init famcls25 | accept19 | 0.9368 | — | — | **IN FLIGHT** |

## Bracket lesson
Encoder LR 1e-5 lifts family but slips structure; 5e-6 holds structure but under-trains family. Mid **7.5e-6** is the authorized protocol probe.

## Policy
1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. Full 40-epoch runs required
4. Agent-owned classification OK; do not invent OBSERVED structure gold
5. Do not deepen N blindly (N=10 hurt)

## Next
1. Finish famcls30 gate (KEEP → pin + dump + accept20; REJECT → next protocol)
2. Hold envelope morphs / BEST overwrite until ladder 0.55 has a real plan
