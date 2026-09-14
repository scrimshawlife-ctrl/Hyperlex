# Spec 007 — famcls35 REJECT; famcls36 accept20+aux climb in flight

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins
| pin | path | note |
|-----|------|------|
| **weight** | `~/hlx-private/p1-structure-unbind-famcls25-20260914/` | last KEEP |
| **data** | `~/hlx-private/p1-classify-accept20-20260914/prepare` | +149 residual |
| **BEST** | morph19 | untouched |

## Latest
| run | recipe | family | structure | verdict |
|-----|--------|--------|-----------|---------|
| fair famcls25 / accept20 | — | **0.9286** | 1.0 | baseline |
| famcls35 | N=8 LR 1e-5 no aux | **0.9286** tie | **0.958** | REJECT |
| famcls36 | N=8 LR 1e-5 aux=0.25 up4 | — | — | **IN FLIGHT** |

## Gate (famcls36)
family > **0.9285714285714286** AND structure/role/pointer == **1.0**.
