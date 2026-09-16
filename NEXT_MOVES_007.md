# Spec 007 — morph40 BEST (INFERRED promote); morph36 preserved

**Authority:** Spec 007 only. `name_gate` false. No Hub. **Labeler authorized.** No invent beyond labeled set.  
**BEST:** **morph40** — `unbind_exact≈0.7368` (ep9) on fair val **n=228**. Prior morph36 artifacts preserved. Climb KEEP famcls52 ≠ BEST.

## Status

morph36 was BEST through morph39 REJECT.  
**Labeler AUTHORIZED 2026-09-16** (METHOD + 136 auth / 10 abstain).  
morph39 OBSERVED-only gold → **REJECT_VS_BEST** vs fair 0.5740 (n=338).  
**110 INFERRED** high-confidence promoted → OBSERVED train (1 punct hold documentary).  
morph40 → **PIN BEST** (best **0.7368** > fair morph36 **0.7325** on n=228). E2 PASS.

## Marks status (2026-09-16)

| mark | status |
|------|--------|
| morph36 BEST | **HIT** then **superseded** (artifacts preserved) |
| morph37 / morph38 warm | **HIT** → REJECT_VS_BEST |
| Danny/operator P1 gold | **HIT** (authorized + labeled) |
| morph39 observed-gold force-train | **HIT** → REJECT_VS_BEST |
| INFERRED→OBSERVED train promote | **HIT** (110 / 1 hold / 10 abstain) |
| morph40 inferred-promote | **HIT** → **PIN BEST** |
| Ladder `unbind_exact` ≥ **0.55** (comparable new val n=228) | **HIT** (0.7368) |

## Civilian scores

| model | val n | unbind_exact | note |
|-------|------:|-------------:|------|
| morph36 old val | 363 | 0.5455 | prior pin surface |
| morph36 fair morph39 | 338 | 0.5740 | after 25 OBSERVED force-train |
| morph39 best ep2 | 338 | 0.5621 | REJECT vs fair |
| **morph36 fair morph40** | **228** | **0.7325** | after 135 force-train |
| **morph40 BEST ep9** | **228** | **0.7368** | **PIN** |
| morph40 final ep39 | 228 | 0.6930 | SAVE_BEST kept ep9 |

## Pins

| pin | path | note |
|-----|------|------|
| **BEST** | morph40 | `...-seed-morph40` |
| morph36 | `...-seed-morph36` | preserved prior BEST |
| morph39 | `...-seed-morph39` | REJECT_VS_BEST |
| **Danny package** | `receipts/danny-gold-review-partial-slot-miss-20260915/` | 135 train-ready |
| **morph40 gate** | `receipts/20260916-morph40-40ep-pin-best.md` | |

## Next

- BEST is morph40. Do not warm-clone without a new documented lever.
- Residual after morph40: **60** (partial_slot_miss 28; positional_head 23; type_slot_token 23; full_miss 15).
- 1 documentary INFERRED hold + 10 abstain stay out of train.
- `name_gate` remains false. No Hub. No invent beyond labeled set.

## Policy

`name_gate=false`. Labeler authorized. Climb KEEP ≠ BEST. Full 40-epoch runs. One documented lever per climb. Fair-eval when val changes. No invent beyond labeled set.
