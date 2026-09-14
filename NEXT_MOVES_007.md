# Spec 007 — famcls33 REJECT; famcls34 upsample=1 climb in flight

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins
| pin | path | note |
|-----|------|------|
| **weight** | `~/hlx-private/p1-structure-unbind-famcls25-20260914/` | last KEEP |
| **data** | `~/hlx-private/p1-classify-accept19-20260914/prepare` | residual |
| **BEST** | morph19 | untouched |

## Bracket (accept19, N=8, LR 1e-5)

| run | aux | upsample | family | structure | verdict |
|-----|-----|----------|--------|-----------|---------|
| famcls28 | 0 | — | **0.9598** | **0.958** | REJECT |
| famcls34 | 0.05 | **1** | — | — | **IN FLIGHT** |
| famcls33 | 0.05 | 4 | **0.9138** | 1.0 | REJECT |
| famcls32 | 0.25 | 4 | **0.9080** | 1.0 | REJECT |
| famcls31 | 1.0 | 4 | **0.9023** | 1.0 | REJECT |

Baseline family: **0.9368**. Must hold structure/role/pointer at **1.0**.

## Next
Finish famcls34. If REJECT → build accept20 residual gold from famcls25 dump, then retry family-lifting LR.
