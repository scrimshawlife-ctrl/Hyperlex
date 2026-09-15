# Spec 007 — famcls52 KEEP; civilian eval done; **waiting on Danny**

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.
**Climb KEEP ≠ BEST.**

## Marks status (2026-09-15 Move-1 EVAL)

| mark | status |
|------|--------|
| Climb holdout family/structure/role/pointer **1.0** on accept29; KEEP **famcls52** | **HIT** |
| Civilian `unbind_exact` receipt famcls52 vs morph19 same val surface | **HIT** → `receipts/climb_vs_best_civilian.json` |
| Ladder `unbind_exact` ≥ **0.55** | **MISS** (morph19 0.4545; climb transfer 0.0028) |
| Exhaust → Danny / OBSERVED `partial_slot_miss` escalate | **HIT** — **waiting on Danny** |

## Civilian scores (n=363 live unbind val)

| model | unbind_exact | token_f1 | slot_f1 | partial_slot_miss |
|-------|-------------:|---------:|--------:|------------------:|
| morph19 BEST | **0.4545** | 0.6976 | 0.6966 | **146** |
| famcls52 transfer | **0.0028** | 0.1015 | 0.0994 | 43 |

No auto-promote. Morph envelope exhausted; climb holdout saturated; wall is OBSERVED `partial_slot_miss`.

## Pins
| pin | path | note |
|-----|------|------|
| **weight (climb KEEP)** | `~/hlx-private/p1-structure-unbind-famcls52-20260914/` | family **1.0** / struct·role·ptr **1.0** — aux=0.35/up=12 — **not** BEST |
| **data** | `~/hlx-private/p1-classify-accept29-20260914/prepare` | +2 family residuals force-train; rows_sha256 `4e151140…46ff` |
| **civilian receipt** | `~/hlx-private/climb_vs_best_civilian.json` | + workspace `specs/007-hyperlexical-model/receipts/` |
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

## Next
- **Blocked on Danny:** settle OBSERVED gold for `partial_slot_miss` (civilian unbind wall) or authorize alternate ladder path
- Do **not** dump→accept→train on climb (no holdout residuals)
- Do **not** auto-promote to BEST; climb KEEP ≠ BEST

## Policy
OBSERVED hold. No BEST overwrite. Climb KEEP ≠ BEST. Full 40-epoch runs. `name_gate=false`.
