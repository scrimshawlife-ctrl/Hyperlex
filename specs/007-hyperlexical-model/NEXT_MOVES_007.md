# Spec 007 — morph35 KEEP_CANDIDATE; Danny gold still pending; BEST=morph19

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545` (**untouched**; morph35 not promoted).
**Climb KEEP ≠ BEST.** famcls52 holdout **1.0**.

## Status

Operator override continue-train while Danny escalate pending.  
Danny gold still **blank** → no accept30. Climb saturated → skipped famcls53.  
Ran **civilian morph35** (morph19 envelope, **epochs=40**, existing hard atoms only) → **KEEP_CANDIDATE** on final val, **no BEST promote**.

## Marks status (2026-09-15)

| mark | status |
|------|--------|
| Climb holdout 1.0; KEEP famcls52 | **HIT** |
| morph35 40ep civilian train (no invented OBSERVED) | **HIT** |
| Gate final exact > morph19 + E2 PASS | **HIT** → KEEP_CANDIDATE |
| Promote BEST → morph35 | **HELD** (operator: without promoting) |
| Ladder `unbind_exact` ≥ **0.55** | **MISS** on **saved** weights (final 0.4904); peak ep16 **0.5372** receipt-only |
| Danny OBSERVED `partial_slot_miss` gold | **PENDING** |

## Civilian scores (n=363 live unbind val)

| model | unbind_exact | token_f1 | slot_f1 | partial_slot_miss |
|-------|-------------:|---------:|--------:|------------------:|
| morph19 BEST | 0.4545 | 0.6976 | 0.6966 | 146 |
| **morph35 final** | **0.4904** | **0.7468** | **0.7457** | **143** |
| morph35 peak ep16 (not saved) | 0.5372 | 0.7628 | 0.7628 | — |
| famcls52 transfer | 0.0028 | 0.1015 | 0.0994 | 43 |

## Pins
| pin | path | note |
|-----|------|------|
| **BEST** | morph19 | **untouched** |
| **KEEP_CANDIDATE (not BEST)** | `~/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph35` | final 0.4904; E2 PASS |
| **climb KEEP** | `~/hlx-private/p1-structure-unbind-famcls52-20260914/` | holdout 1.0 |
| **Danny package** | `specs/007-hyperlexical-model/receipts/danny-gold-review-partial-slot-miss-20260915/` | gold blank |
| **receipt** | `specs/007-hyperlexical-model/receipts/20260915-morph35-40ep-keep-candidate.md` | + bundle dir |

## Next
- Waiting on Danny for OBSERVED structure gold (or explicit promote of morph35 / best-ckpt work)
- Do not invent OBSERVED gold; do not overwrite BEST without promote yes
- Optional follow-up: checkpoint-best save (ep16 0.5372) if authorized — still name_gate false

## Policy
OBSERVED hold. No BEST overwrite. Climb KEEP ≠ BEST. Full 40-epoch runs. `name_gate=false`.
