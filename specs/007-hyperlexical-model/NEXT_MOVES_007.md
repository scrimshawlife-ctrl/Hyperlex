# Spec 007 — morph36 BEST; morph38 warm REJECT_VS_BEST (LR 1e-5)

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** **morph36** — `unbind_exact≈0.5455` (operator promote; morph19 preserved).
**Climb KEEP ≠ BEST.** famcls52 holdout **1.0**.

## Status

morph36 promoted → BEST (operator yes).  
morph37 warm (LR 2e-5) → **REJECT_VS_BEST** (best 0.5317).  
morph38 warm (LR **1e-5**, one lever vs morph37) → **REJECT_VS_BEST** (best 0.5234 < 0.5455; E2 PASS).  
Danny gold still **blank** → no accept30 / no invented OBSERVED.

## Marks status (2026-09-15)

| mark | status |
|------|--------|
| morph35 KEEP on Hyperlex main | **HIT** (PR #68) |
| morph36 40ep + best-ckpt save | **HIT** |
| Promote BEST → morph36 | **HIT** (0.5455 > morph19 0.4545) |
| morph37 warm 40ep | **HIT** → **REJECT_VS_BEST** |
| morph38 warm LR 1e-5 | **HIT** → **REJECT_VS_BEST** |
| Ladder `unbind_exact` ≥ **0.55** | **MISS** (morph36 0.5455; morph37 0.5317; morph38 0.5234) |
| Danny OBSERVED `partial_slot_miss` gold | **PENDING** |

## Civilian scores (n=363 live unbind val)

| model | unbind_exact | token_f1 | slot_f1 | partial_slot_miss |
|-------|-------------:|---------:|--------:|------------------:|
| morph19 (prior BEST, preserved) | 0.4545 | 0.6976 | 0.6966 | 146 |
| morph35 final KEEP | 0.4904 | 0.7468 | 0.7457 | 143 |
| **morph36 BEST ep23** | **0.5455** | **0.7714** | **0.7714** | **134** |
| morph36 final | 0.5124 | — | — | — |
| morph37 best ep2 (warm LR 2e-5) | 0.5317 | 0.7682 | 0.7671 | 139 |
| morph37 final | 0.5014 | — | — | — |
| morph38 best ep2 (warm LR 1e-5) | 0.5234 | 0.7660 | 0.7660 | 140 |
| morph38 final | 0.4656 | — | — | — |

## Pins
| pin | path | note |
|-----|------|------|
| **BEST** | morph36 | held after morph38 reject |
| prior BEST (archived) | morph19 | intact |
| morph37 | `...-seed-morph37` | REJECT_VS_BEST; E2 PASS |
| morph38 | `...-seed-morph38` | REJECT_VS_BEST; E2 PASS; LR 1e-5 |
| **Danny package** | `specs/007-hyperlexical-model/receipts/danny-gold-review-partial-slot-miss-20260915/` | gold blank |
| **promote receipt** | `specs/007-hyperlexical-model/receipts/20260915-morph36-promote-best.md` | |
| **morph37 gate** | `specs/007-hyperlexical-model/receipts/20260915-morph37-40ep-reject-vs-best.md` | |
| **morph38 gate** | `specs/007-hyperlexical-model/receipts/20260915-morph38-40ep-reject-vs-best.md` | |

## Next
- Waiting on **Danny gold** for OBSERVED `partial_slot_miss` / accept30+ (**do not invent**)
- Ladder `unbind_exact` ≥ **0.55** still **MISS** (morph36 0.5455 closest)
- Warm continue ± LR failed to beat morph36; next climb needs a **non-schedule/LR** lever (gold or loss/data) — do not start morph39 as another warm clone

## Policy
OBSERVED hold. Climb KEEP ≠ BEST. Full 40-epoch runs. `name_gate=false`. One documented lever per climb (morph38 = LR 1e-5 vs morph37 — REJECT).
