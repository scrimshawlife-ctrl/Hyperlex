# Spec 007 — famcls47 REJECT; famcls48 aux=0.35/up=12 in flight

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**. Climb KEEP ≠ BEST.

## Pins
| pin | path | note |
|-----|------|------|
| **weight (climb KEEP)** | `~/hlx-private/p1-structure-unbind-famcls46-20260914/` | **KEEP** — family 0.9899; structure hold — **not** BEST |
| **data** | `~/hlx-private/p1-classify-accept25-20260914/prepare` | +24 force-train residuals |
| **BEST** | morph19 | **untouched** |

## famcls47 REJECT (accept25)
family **0.9949** > 0.9899 PASS; structure/pointer **0.958** FAIL (23/24).
Hole: `sheesh moment` positional pointer off-by-one (slot1 3→2) — same as famcls43/44.

## Gate (famcls48) — IN FLIGHT
Init famcls46 · accept25 · N=8 · LR 5e-6 · **aux=0.35** · **upsample=12** · 40 ep.
family > **0.98989898989899** AND structure/role/pointer == **1.0**.

## Policy
OBSERVED hold. No BEST overwrite. Full 40-epoch runs. Raise aux/upsample on structure slip; do not clone identical.
