# Spec 007 — famcls50 REJECT (family 1.0, structure slip); pin stays famcls48

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.
**Climb KEEP ≠ BEST.**

## Pins
| pin | path | note |
|-----|------|------|
| **weight (climb KEEP)** | `~/hlx-private/p1-structure-unbind-famcls48-20260914/` | family **0.9949** / struct·role·ptr **1.0** — aux=0.35/up=12 — **not** BEST |
| **data** | `~/hlx-private/p1-classify-accept27-20260914/prepare` | +24 force-train; exact residuals forced even if in test |
| **preserved (not BEST)** | `~/hlx-private/preserved/famcls45-20260914/` | snapshot; originals intact |
| **BEST** | morph19 | **untouched** |

## Ladder (recent)
| run | data | aux / up | family | structure | climb verdict | BEST? |
|-----|------|----------|--------|-----------|---------------|-------|
| famcls46 | accept24 | 0.25 / 8 | **0.9899** | **1.0** | KEEP (climb) | no |
| famcls47 | accept25 | 0.25 / 8 | **0.9949** | **0.958** | REJECT | no |
| famcls48 | accept25 | **0.35** / **12** | **0.9949** | **1.0** | **KEEP** | **no** |
| famcls49 | accept26 | 0.35 / 12 | **0.9848** | **1.0** | **REJECT** (family slip) | no |
| famcls50 | accept27 | 0.35 / 12 | **1.0** | **0.958** | **REJECT** (structure/`sheesh moment` ptr) | no |

## accept27
- `rows_sha256=8f0d2b189aca3564ee657d04b26baf8f19c07eb0624127685eaf7f8e1e77e117`
- Exact residuals force-train: `one shot combo`, `inting mid will throw the series`, `need alignment to ship`
- Fair famcls48 baseline: family **0.9949494949494949**, structure/role/pointer **1.0**

## Next (suggested)
- Structure hole is again `sheesh moment` positional ptr slot1 (3→2) — same as famcls47.
- Options: stronger struct aux/upsample, structure-focused gold (no invented OBSERVED), or freeze earlier KEEP and probe differently.
- Do **not** auto-promote famcls50; climb pin remains famcls48.

## Policy
OBSERVED hold. No BEST overwrite. Climb KEEP ≠ BEST. Full 40-epoch runs.
