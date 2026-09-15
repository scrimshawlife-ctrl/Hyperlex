# Spec 007 — **waiting on Danny**; gold review package ready; **no train**

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.
**Climb KEEP ≠ BEST.** famcls52 holdout **1.0** — **no climb residuals**.

## Status

**Blocked on Danny.** Civilian morph19 wall is OBSERVED `partial_slot_miss` (**146**).  
Danny-ready gold review package is filed — **do not train** (no famcls53, no morph
envelope, no BEST overwrite) until Danny authorizes OBSERVED structure gold **or**
an alternate ladder path.

**Package:** `specs/007-hyperlexical-model/receipts/danny-gold-review-partial-slot-miss-20260915/`  
→ start at `ASK_DANNY.md` · manifest · `candidates.jsonl` (blank gold) · `PATTERN_RANK.md`

## Marks status (2026-09-15)

| mark | status |
|------|--------|
| Climb holdout family/structure/role/pointer **1.0** on accept29; KEEP **famcls52** | **HIT** |
| Civilian `unbind_exact` receipt famcls52 vs morph19 same val surface | **HIT** → `receipts/climb_vs_best_civilian.json` |
| Ladder `unbind_exact` ≥ **0.55** | **MISS** (morph19 0.4545; climb transfer 0.0028) |
| Exhaust → Danny / OBSERVED `partial_slot_miss` escalate | **HIT** — **waiting on Danny** |
| Danny gold review package (blank gold; schemes positional\|type_slot) | **HIT** — package linked above |

## Civilian scores (n=363 live unbind val)

| model | unbind_exact | token_f1 | slot_f1 | partial_slot_miss |
|-------|-------------:|---------:|--------:|------------------:|
| morph19 BEST | **0.4545** | 0.6976 | 0.6966 | **146** |
| famcls52 transfer | **0.0028** | 0.1015 | 0.0994 | 43 |

## Explicit no-train gate

Until Danny authorize:

- **No** famcls53 / further climb dump→accept→train (holdout saturated)
- **No** morph envelope trains; **do not touch BEST morph19**
- **No** invented OBSERVED gold; package gold fields stay blank for human fill
- `name_gate=false`; no BEST overwrite; climb KEEP ≠ BEST

## Pins
| pin | path | note |
|-----|------|------|
| **weight (climb KEEP)** | `~/hlx-private/p1-structure-unbind-famcls52-20260914/` | family **1.0** / struct·role·ptr **1.0** — **not** BEST |
| **data** | `~/hlx-private/p1-classify-accept29-20260914/prepare` | +2 family residuals force-train; rows_sha256 `4e151140…46ff` |
| **civilian receipt** | `~/hlx-private/climb_vs_best_civilian.json` | + workspace `specs/007-hyperlexical-model/receipts/` |
| **Danny review package** | `specs/007-hyperlexical-model/receipts/danny-gold-review-partial-slot-miss-20260915/` | n_residual=198; P1 partial_slot_miss=146 |
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
- **Waiting on Danny:** review package → authorize OBSERVED structure gold **or** alternate ladder path
- Do **not** start famcls53 / morph trains; do **not** touch BEST morph19

## Policy
OBSERVED hold. No BEST overwrite. Climb KEEP ≠ BEST. Full 40-epoch runs. `name_gate=false`. **No train until authorize.**
