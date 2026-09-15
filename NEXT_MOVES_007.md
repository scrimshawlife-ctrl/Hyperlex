# Spec 007 — morph36 BEST; morph38 warm IN FLIGHT (LR 1e-5)

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** **morph36** — `unbind_exact≈0.5455` (operator promote; morph19 preserved).
**Climb KEEP ≠ BEST.** famcls52 holdout **1.0**.

## Status

morph36 promoted → BEST (operator yes).  
morph37 warm from morph36 (40ep, LR 2e-5, `SAVE_BEST_UNBIND=1`) → **REJECT_VS_BEST** (best 0.5317 < 0.5455; E2 PASS).  
**morph38** warm from morph36 — **one lever vs morph37: LR 1e-5** (morph37 peaked ep2 then regressed under 2e-5) — **IN FLIGHT**.  
Danny gold still **blank** → no accept30 / no invented OBSERVED.

## Marks status (2026-09-15)

| mark | status |
|------|--------|
| morph35 KEEP on Hyperlex main | **HIT** (PR #68) |
| morph36 40ep + best-ckpt save | **HIT** |
| Promote BEST → morph36 | **HIT** (0.5455 > morph19 0.4545) |
| morph37 warm 40ep | **HIT** → **REJECT_VS_BEST** |
| morph38 warm LR 1e-5 | **IN FLIGHT** |
| Ladder `unbind_exact` ≥ **0.55** | **MISS** (morph36 0.5455; morph37 0.5317) |
| Danny OBSERVED `partial_slot_miss` gold | **PENDING** |

## Civilian scores (n=363 live unbind val)

| model | unbind_exact | token_f1 | slot_f1 | partial_slot_miss |
|-------|-------------:|---------:|--------:|------------------:|
| morph19 (prior BEST, preserved) | 0.4545 | 0.6976 | 0.6966 | 146 |
| morph35 final KEEP | 0.4904 | 0.7468 | 0.7457 | 143 |
| **morph36 BEST ep23** | **0.5455** | **0.7714** | **0.7714** | **134** |
| morph36 final | 0.5124 | — | — | — |
| morph37 best ep2 (warm) | 0.5317 | 0.7682 | 0.7671 | 139 |
| morph37 final | 0.5014 | — | — | — |
| morph38 | *pending* | | | |

## Pins
| pin | path | note |
|-----|------|------|
| **BEST** | morph36 | held during morph38 train |
| prior BEST (archived) | morph19 | intact |
| morph37 | `...-seed-morph37` | REJECT_VS_BEST; E2 PASS |
| morph38 | `...-seed-morph38` | IN FLIGHT; LR 1e-5 |
| **Danny package** | `specs/007-hyperlexical-model/receipts/danny-gold-review-partial-slot-miss-20260915/` | gold blank |
| **promote receipt** | `specs/007-hyperlexical-model/receipts/20260915-morph36-promote-best.md` | |
| **morph37 gate** | `specs/007-hyperlexical-model/receipts/20260915-morph37-40ep-reject-vs-best.md` | |
| **morph38 inflight** | `specs/007-hyperlexical-model/receipts/20260915-morph38-40ep-inflight.md` | |

## Next
- Finish morph38 gate vs morph36 BEST (promote if exact > 0.5455)
- Waiting on **Danny gold** for OBSERVED `partial_slot_miss` / accept30+ (**do not invent**)
- Ladder `unbind_exact` ≥ **0.55** still **MISS** until morph38 (or later) clears

## Policy
OBSERVED hold. Climb KEEP ≠ BEST. Full 40-epoch runs. `name_gate=false`. One documented lever per climb (morph38 = LR 1e-5 vs morph37).
