# Spec 007 — morph36 BEST; morph37 warm 40ep IN FLIGHT

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** **morph36** — `unbind_exact≈0.5455` (operator promote yes; prior morph19 preserved).
**Climb KEEP ≠ BEST.** famcls52 holdout **1.0**.

## Status

Operator granted **promote morph36 → BEST** and continue-train morph37.  
Danny gold still **blank** → no accept30 / no invented OBSERVED.  
**morph37** warm from morph36 BEST, epochs=40, `HYPERLEX_SAVE_BEST_UNBIND=1`, new out dir — **IN FLIGHT** (does not clobber BEST mid-train).

## Marks status (2026-09-15)

| mark | status |
|------|--------|
| morph35 KEEP on Hyperlex main | **HIT** (PR #68) |
| morph36 40ep + best-ckpt save | **HIT** |
| Promote BEST → morph36 | **HIT** (operator yes; 0.5455 > morph19 0.4545) |
| morph37 warm 40ep | **IN FLIGHT** |
| Ladder `unbind_exact` ≥ **0.55** | **MISS** on morph36 best (**0.5455**); morph37 targeting |
| Danny OBSERVED `partial_slot_miss` gold | **PENDING** |

## Civilian scores (n=363 live unbind val)

| model | unbind_exact | token_f1 | slot_f1 | partial_slot_miss |
|-------|-------------:|---------:|--------:|------------------:|
| morph19 (prior BEST, preserved) | 0.4545 | 0.6976 | 0.6966 | 146 |
| morph35 final KEEP | 0.4904 | 0.7468 | 0.7457 | 143 |
| **morph36 BEST ep23** | **0.5455** | **0.7714** | **0.7714** | **134** |
| morph36 final | 0.5124 | — | — | — |
| morph37 | *in flight* | | | |

## Pins
| pin | path | note |
|-----|------|------|
| **BEST** | morph36 | **promoted** (operator grant); prior morph19 intact |
| prior BEST (archived) | morph19 | mtime unchanged; not deleted |
| prior KEEP | morph35 | final 0.4904; still on disk |
| morph37 out | `~/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph37` | new; not BEST until gate |
| **climb KEEP** | `~/hlx-private/p1-structure-unbind-famcls52-20260914/` | holdout 1.0 |
| **Danny package** | `specs/007-hyperlexical-model/receipts/danny-gold-review-partial-slot-miss-20260915/` | gold blank |
| **promote receipt** | `specs/007-hyperlexical-model/receipts/20260915-morph36-promote-best.md` | + spark private |
| **morph37 inflight** | `specs/007-hyperlexical-model/receipts/20260915-morph37-40ep-inflight.md` | |

## Next
- Finish morph37 40ep; gate vs morph36 BEST; promote if ≥ morph36 (prefer ≥0.55)
- Danny gold still required for OBSERVED `partial_slot_miss` / accept30+
- Do not invent OBSERVED gold

## Policy
OBSERVED hold. Climb KEEP ≠ BEST. Full 40-epoch runs. `name_gate=false`.
