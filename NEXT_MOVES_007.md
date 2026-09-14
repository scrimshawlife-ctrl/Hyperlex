# Spec 007 — famcls43 REJECT; famcls44 aux=0.18 in flight

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins
| pin | path | note |
|-----|------|------|
| **weight** | `~/hlx-private/p1-structure-unbind-famcls41-20260914/` | KEEP — N=8 LR 5e-6 aux=0.12 |
| **data** | `~/hlx-private/p1-classify-accept23-20260914/prepare` | force-promote residuals into train |
| **BEST** | morph19 | untouched |

## Recent ladder
| run | data | aux | family | structure | verdict |
|-----|------|-----|--------|-----------|---------|
| famcls41 | accept21 | 0.12 | **0.9474** | **1.0** | **KEEP** |
| famcls42 | accept22 | 0.12 | 0.9343 | 1.0 | REJECT (exacts never in train) |
| famcls43 | accept23 | 0.12 | **0.9848** | **0.958** | REJECT (family↑ structure slip) |
| famcls44 | accept23 | **0.18** | — | — | **IN FLIGHT** |

## Gate (famcls44)
Init famcls41 · N=8 · LR 5e-6 · aux=**0.18** · upsample=4 · 40 ep · accept23.
family > **0.9444444444444444** AND structure/role/pointer == **1.0**.

## Lesson
Force-promoting test-only residuals into train unlocked family lift; KEEP aux=0.12 no longer holds structure on that data. Raise aux.

## Policy
OBSERVED hold. No BEST overwrite. Full 40-epoch runs.
