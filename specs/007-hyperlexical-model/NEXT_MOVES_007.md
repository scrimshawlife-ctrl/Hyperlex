# Spec 007 — morph36 KEEP_CANDIDATE (best-ckpt); BEST=morph19 held

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545` (**untouched**; morph36 not promoted).
**Climb KEEP ≠ BEST.** famcls52 holdout **1.0**.

## Status

Operator continue-train while Danny escalate pending.  
Danny gold still **blank** → no accept30.  
Ran **civilian morph36** (morph19 envelope, **epochs=40**, `HYPERLEX_SAVE_BEST_UNBIND=1`, trunk init — not warm morph35 final) → **KEEP_CANDIDATE** on **best-saved** val, **no BEST promote**.

## Marks status (2026-09-15)

| mark | status |
|------|--------|
| morph35 KEEP on Hyperlex main | **HIT** (PR #68) |
| morph36 40ep + best-ckpt save | **HIT** |
| Gate best exact > morph35 + E2 PASS | **HIT** → KEEP_CANDIDATE |
| Promote BEST → morph36 | **HELD** (near 0.55; needs operator yes) |
| Ladder `unbind_exact` ≥ **0.55** | **MISS** on saved best (**0.5455**) |
| Danny OBSERVED `partial_slot_miss` gold | **PENDING** |

## Civilian scores (n=363 live unbind val)

| model | unbind_exact | token_f1 | slot_f1 | partial_slot_miss |
|-------|-------------:|---------:|--------:|------------------:|
| morph19 BEST | 0.4545 | 0.6976 | 0.6966 | 146 |
| morph35 final KEEP | 0.4904 | 0.7468 | 0.7457 | 143 |
| morph35 peak ep16 (unsaved) | 0.5372 | 0.7628 | 0.7628 | — |
| **morph36 best ep23 (saved)** | **0.5455** | **0.7714** | **0.7714** | **134** |
| morph36 final | 0.5124 | — | — | — |

## Pins
| pin | path | note |
|-----|------|------|
| **BEST** | morph19 | **untouched** |
| **KEEP_CANDIDATE (not BEST)** | `~/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph36` | best 0.5455; E2 PASS |
| prior KEEP | morph35 | final 0.4904; still on disk |
| **climb KEEP** | `~/hlx-private/p1-structure-unbind-famcls52-20260914/` | holdout 1.0 |
| **Danny package** | `specs/007-hyperlexical-model/receipts/danny-gold-review-partial-slot-miss-20260915/` | gold blank |
| **receipt** | `specs/007-hyperlexical-model/receipts/20260915-morph36-40ep-keep-candidate.md` | + bundle dir |

## Next
- Waiting on Danny for OBSERVED structure gold (or explicit **promote yes** for morph36 → BEST)
- Do not invent OBSERVED gold; do not overwrite BEST without promote yes
- Peak-not-saved fixed via `HYPERLEX_SAVE_BEST_UNBIND=1`

## Policy
OBSERVED hold. No BEST overwrite. Climb KEEP ≠ BEST. Full 40-epoch runs. `name_gate=false`.
