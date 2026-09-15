# Spec 007 — accept29 merge; famcls52 training (aux=0.35/12)

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.
**Climb KEEP ≠ BEST.**

## Pins
| pin | path | note |
|-----|------|------|
| **weight (climb KEEP)** | `~/hlx-private/p1-structure-unbind-famcls48-20260914/` | family **0.9949** / struct·role·ptr **1.0** — aux=0.35/up=12 — **not** BEST |
| **data** | `~/hlx-private/p1-classify-accept29-20260914/prepare` | +2 family residuals force-train; rows_sha256 `4e151140…46ff` |
| **preserved (not BEST)** | `~/hlx-private/preserved/famcls45-20260914/` | snapshot; originals intact |
| **BEST** | morph19 | **untouched** |

## Ladder (recent)
| run | data | aux / up | family | structure | climb verdict | BEST? |
|-----|------|----------|--------|-----------|---------------|-------|
| famcls48 | accept25 | **0.35** / **12** | **0.9949** | **1.0** | **KEEP** | **no** |
| famcls49 | accept26 | 0.35 / 12 | **0.9848** | **1.0** | REJECT (family) | no |
| famcls50 | accept27 | 0.35 / 12 | **1.0** | **0.958** | REJECT (`sheesh` ptr) | no |
| famcls51 | accept28 | **0.40** / **16** | **0.9899** | **1.0** | **REJECT** (family; sheesh closed) | no |
| famcls52 | accept29 | **0.35** / **12** | — | — | **IN FLIGHT** | — |

## accept29 / famcls52
- Force-train residuals from famcls51 dump: `escalate to the em` (workplace-corp), `quiet elevator rizz with zero words` (brainrot-aura) + contrastives
- Inherit accept28 sheesh structure gold clones (no new OBSERVED structure)
- Fair famcls48 on accept29-test: family **0.9949494949494949**, structure/role/pointer **1.0**
- Recipe: return to famcls48 KEEP **aux=0.35/up=12** (0.40/16 closed sheesh but slipped family)
- Gate: family > baseline AND struct/role/ptr = 1.0; init famcls48; 40 ep

## Policy
OBSERVED hold. No BEST overwrite. Climb KEEP ≠ BEST. Full 40-epoch runs.
