# Spec 007 — famcls46 KEEP; accept25 + famcls47 in flight

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins
| pin | path | note |
|-----|------|------|
| **weight** | `~/hlx-private/p1-structure-unbind-famcls46-20260914/` | **KEEP** — N=8 LR 5e-6 aux=0.25 up=8 |
| **data** | `~/hlx-private/p1-classify-accept25-20260914/prepare` | +24 force-train residuals |
| **BEST** | morph19 | untouched |

## famcls46 KEEP (accept24)
family **0.9899** > baseline 0.9545; structure/role/pointer **1.0** (best ep 1).
KEEP recipe held; large family lift with structure intact.

## accept25
+24 train force-promotes for 2 famcls46 residuals (`one shot combo`, `ser so back onchain`).
Fair famcls46 on accept25-test: family **0.98989898989899**, structure/role/pointer **1.0**.

## Gate (famcls47) — IN FLIGHT
Init famcls46 · N=8 · LR 5e-6 · aux=0.25 · upsample=8 · 40 ep · accept25.
family > **0.98989898989899** AND structure/role/pointer == **1.0**.

## Policy
OBSERVED hold. No BEST overwrite. Full 40-epoch runs.
