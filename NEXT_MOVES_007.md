# Spec 007 — famcls48 KEEP; accept26 + famcls49 in flight; BEST unchanged

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.
**Climb KEEP ≠ BEST.** Human review + Danny `name_gate` required before any promotion.

## Pins
| pin | path | note |
|-----|------|------|
| **weight (climb KEEP)** | `~/hlx-private/p1-structure-unbind-famcls48-20260914/` | family **0.9949** / struct·role·ptr **1.0** — aux=0.35/up=12 — **not** BEST |
| **data** | `~/hlx-private/p1-classify-accept26-20260914/prepare` | +14 force-train (`sigma grindset`) |
| **preserved (not BEST)** | `~/hlx-private/preserved/famcls45-20260914/` | snapshot; originals intact |
| **BEST** | morph19 | **untouched** |

## Ladder (recent)
| run | data | aux / up | family | structure | climb verdict | BEST? |
|-----|------|----------|--------|-----------|---------------|-------|
| famcls46 | accept24 | 0.25 / 8 | **0.9899** | **1.0** | KEEP (climb) | **no** |
| famcls47 | accept25 | 0.25 / 8 | **0.9949** | **0.958** | **REJECT** | no |
| famcls48 | accept25 | **0.35** / **12** | **0.9949** | **1.0** | **KEEP** | **no** |
| famcls49 | accept26 | 0.35 / 12 | — | — | **IN FLIGHT** | — |

## famcls48 KEEP
Init famcls46 · accept25 · aux=0.35 · up=12 · 40 ep (best 6).  
family **0.9949** > 0.9899; structure/role/pointer **1.0**. Closed `sheesh moment` hole.

## accept26
+14 train force-promotes for 1 residual: `sigma grindset` (brainrot→ai-native).  
Fair famcls48 on accept26-test: family **0.9949494949494949**, structure/role/pointer **1.0**.

## Gate (famcls49) — IN FLIGHT
Init famcls48 · accept26 · N=8 · LR 5e-6 · aux=0.35 · upsample=12 · 40 ep.  
family > **0.9949494949494949** AND structure/role/pointer == **1.0**.

## Policy
OBSERVED hold. No BEST overwrite. Full 40-epoch runs. Climb KEEP ≠ BEST.
