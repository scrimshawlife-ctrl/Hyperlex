# Spec 007 — famcls31 REJECT; famcls32 aux-weight 0.25 climb in flight

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins

| pin | path | note |
|-----|------|------|
| **weight joint (family-line)** | `~/hlx-private/p1-structure-unbind-famcls25-20260914/` | last KEEP; last-N=8 on accept17 |
| **data pin** | `~/hlx-private/p1-classify-accept19-20260914/prepare` | residual after deepen fail |
| reject (do not init) | famcls24,26–31 | see receipts |
| **BEST** | morph19 | untouched |

## Recent gates

| run | recipe | family | structure | verdict |
|-----|--------|--------|-----------|---------|
| famcls25 | N=8 | **0.9304** | 1.0 | **KEEP** |
| famcls28 | N=8 LR 1e-5 | **0.9598** | **0.958** | REJECT |
| famcls29 | N=8 LR 5e-6 | **0.9195** | 1.0 | REJECT |
| famcls30 | N=8 LR 7.5e-6 | **0.9195** | **0.958** | REJECT |
| famcls31 | N=8 LR 1e-5 aux=1.0 | **0.9023** | **1.0** | REJECT |
| famcls32 | N=8 LR 1e-5 aux=**0.25** | — | — | **IN FLIGHT** |

## Protocol lesson
Structure aux at weight 1.0 holds structure but kills family lift. Aux=0 lifts family but slips structure. Bracket aux weight next (0.25).

## Policy
1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. Full 40-epoch runs required
4. Do not deepen N blindly

## Next
Finish famcls32 gate; if REJECT, try aux=0.5 or refresh accept20 residual gold.
