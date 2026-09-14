# Spec 007 — famcls42 REJECT; accept23 + famcls43 in flight

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins
| pin | path | note |
|-----|------|------|
| **weight** | `~/hlx-private/p1-structure-unbind-famcls41-20260914/` | KEEP — N=8 LR 5e-6 aux=0.12 |
| **data** | `~/hlx-private/p1-classify-accept23-20260914/prepare` | force-promote residuals into train |
| **BEST** | morph19 | untouched |

## famcls41 KEEP (accept21)
family **0.9474** / structure·role·pointer **1.0** (aux=0.12 sweet spot).

## famcls42 REJECT (accept22)
Init famcls41 · aux=0.12 · 40 ep (best 3).
family **0.9343** < baseline **0.9444** (structure held 1.0).
accept22 +89 paraphrases skipped exact holdout misses (already test-covered) — never entered train.

## accept23
+35 **train** force-promotes of exact residuals + near variants.
Fair famcls41 on accept23-test: family **0.9444444444444444**, structure/role/pointer **1.0**.

## Gate (famcls43) — IN FLIGHT
Init famcls41 · N=8 · LR 5e-6 · aux=0.12 · upsample=4 · 40 ep · accept23.
family > **0.9444444444444444** AND structure/role/pointer == **1.0**.

## Policy
OBSERVED hold. No BEST overwrite. Full 40-epoch runs.
