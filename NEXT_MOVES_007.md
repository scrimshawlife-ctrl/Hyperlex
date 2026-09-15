# Spec 007 — morph36 40ep IN FLIGHT (best-ckpt); morph35 KEEP; BEST=morph19

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545` (**untouched**).
**Climb KEEP ≠ BEST.** famcls52 holdout **1.0**.
**KEEP_CANDIDATE (not BEST):** morph35 final 0.4904 (peak ep16 0.5372 unsaved).

## Status

morph35 KEEP on Hyperlex `main` (PR #68). Danny gold still **PENDING**.  
**morph36** launched: morph19 envelope, **epochs=40**, `HYPERLEX_SAVE_BEST_UNBIND=1`, trunk init (not warm morph35 final), existing hard atoms only. New out dir — does not overwrite BEST or morph35.

## Marks status (2026-09-15)

| mark | status |
|------|--------|
| morph35 KEEP receipts on Hyperlex main | **HIT** (PR #68) |
| morph36 40ep + best-ckpt save launched | **IN FLIGHT** |
| Promote BEST | **HELD** |
| Danny OBSERVED `partial_slot_miss` gold | **PENDING** |
| Ladder `unbind_exact` ≥ **0.55** | open (morph35 peak 0.5372 near; awaiting morph36 best) |

## Civilian scores (n=363) — prior pins

| model | unbind_exact | token_f1 | slot_f1 | partial_slot_miss |
|-------|-------------:|---------:|--------:|------------------:|
| morph19 BEST | 0.4545 | 0.6976 | 0.6966 | 146 |
| morph35 final KEEP | 0.4904 | 0.7468 | 0.7457 | 143 |
| morph35 peak ep16 (unsaved) | 0.5372 | 0.7628 | 0.7628 | — |
| morph36 | — | — | — | IN FLIGHT |

## Pins
| pin | path | note |
|-----|------|------|
| **BEST** | morph19 | **untouched** |
| **KEEP_CANDIDATE** | morph35 | final 0.4904; not promoted |
| **in flight** | `…-seed-morph36` | best-ckpt primary |
| **Danny package** | `…/danny-gold-review-partial-slot-miss-20260915/` | gold blank |
| **receipt** | `receipts/20260915-morph36-40ep-inflight.md` | |

## Next
- Poll morph36 → gate vs morph19 + morph35; KEEP_CANDIDATE if beats morph35 without promote
- Danny gold still required — do not invent OBSERVED
- Do not overwrite BEST without explicit promote yes

## Policy
OBSERVED hold. No BEST overwrite. Climb KEEP ≠ BEST. Full 40-epoch runs. `name_gate=false`.
