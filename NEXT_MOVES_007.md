# Spec 007 — famcls44 REJECT; famcls45 aux=0.25/up8 in flight

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins
| pin | path | note |
|-----|------|------|
| **weight** | `~/hlx-private/p1-structure-unbind-famcls41-20260914/` | KEEP — N=8 LR 5e-6 aux=0.12 |
| **data** | `~/hlx-private/p1-classify-accept23-20260914/prepare` | force-promote residuals into train |
| **BEST** | morph19 | untouched |

## Recent ladder
| run | aux | up | family | structure | verdict |
|-----|-----|-----|--------|-----------|---------|
| famcls41 | 0.12 | 4 | **0.9474** | **1.0** | **KEEP** (accept21) |
| famcls42 | 0.12 | 4 | 0.9343 | 1.0 | REJECT (exacts never in train) |
| famcls43 | 0.12 | 4 | **0.9848** | **0.958** | REJECT |
| famcls44 | 0.18 | 4 | **0.9697** | **0.958** | REJECT |
| famcls45 | **0.25** | **8** | — | — | **IN FLIGHT** |

## Structure miss (famcls44 dump)
One holdout miss: `"sheesh moment"` positional — role OK; pointer slot1 gold_start=3 pred_start=2.

## Gate (famcls45)
Init famcls41 · accept23 · N=8 · LR 5e-6 · aux=**0.25** · upsample=**8** · 40 ep.
family > **0.9444444444444444** AND structure/role/pointer == **1.0**.

## Policy
OBSERVED hold. No BEST overwrite. Full 40-epoch runs.
