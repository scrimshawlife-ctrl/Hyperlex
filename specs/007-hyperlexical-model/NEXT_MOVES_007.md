# Spec 007 — famcls32 REJECT; famcls33 aux=0.05 climb in flight

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins

| pin | path | note |
|-----|------|------|
| **weight joint (family-line)** | `~/hlx-private/p1-structure-unbind-famcls25-20260914/` | last KEEP |
| **data pin** | `~/hlx-private/p1-classify-accept19-20260914/prepare` | residual |
| **BEST** | morph19 | untouched |

## Aux-weight bracket

| run | aux | family | structure | verdict |
|-----|-----|--------|-----------|---------|
| famcls28 | 0 | **0.9598** | **0.958** | REJECT |
| famcls33 | **0.05** | — | — | **IN FLIGHT** |
| famcls32 | 0.25 | **0.9080** | **1.0** | REJECT |
| famcls31 | 1.0 | **0.9023** | **1.0** | REJECT |

Baseline family to beat: **0.9368**. Structure/role/pointer must stay **1.0**.

## Policy
OBSERVED hold. No BEST overwrite. Full 40-epoch runs. Do not deepen N blindly.

## Next
Finish famcls33. If REJECT, try aux=0.1 or refresh accept20 residual gold then retry LR 1e-5.
