# Spec 007 — famcls52 KEEP (family 1.0 / struct 1.0); pin moves off famcls48

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.
**Climb KEEP ≠ BEST.**

## Pins
| pin | path | note |
|-----|------|------|
| **weight (climb KEEP)** | `~/hlx-private/p1-structure-unbind-famcls52-20260914/` | family **1.0** / struct·role·ptr **1.0** — aux=0.35/up=12 — **not** BEST |
| **data** | `~/hlx-private/p1-classify-accept29-20260914/prepare` | +2 family residuals force-train; rows_sha256 `4e151140…46ff` |
| **preserved (not BEST)** | `~/hlx-private/preserved/famcls45-20260914/` | snapshot; originals intact |
| **BEST** | morph19 | **untouched** |

## Ladder (recent)
| run | data | aux / up | family | structure | climb verdict | BEST? |
|-----|------|----------|--------|-----------|---------------|-------|
| famcls48 | accept25 | **0.35** / **12** | **0.9949** | **1.0** | KEEP (prior) | no |
| famcls49 | accept26 | 0.35 / 12 | **0.9848** | **1.0** | REJECT (family) | no |
| famcls50 | accept27 | 0.35 / 12 | **1.0** | **0.958** | REJECT (`sheesh` ptr) | no |
| famcls51 | accept28 | **0.40** / **16** | **0.9899** | **1.0** | REJECT (family; sheesh closed) | no |
| famcls52 | accept29 | **0.35** / **12** | **1.0** | **1.0** | **KEEP** | **no** |

## accept29 / famcls52 outcome
- Force-train residuals: `escalate to the em`, `quiet elevator rizz with zero words` (+ contrastives)
- Inherit accept28 sheesh structure clones (no invented OBSERVED)
- Fair famcls48 on accept29-test baseline **0.9949** / struct 1.0
- Recipe: **aux=0.35/up=12** (prefer KEEP over 0.40/16) · 40 ep · best 8
- Holdout: family **1.0** > baseline; structure/role/pointer **1.0**

## Next (suggested)
- Continue climb from famcls52 KEEP; dump residuals only if a later run slips
- Do **not** auto-promote to BEST; climb KEEP ≠ BEST

## Policy
OBSERVED hold. No BEST overwrite. Climb KEEP ≠ BEST. Full 40-epoch runs.
