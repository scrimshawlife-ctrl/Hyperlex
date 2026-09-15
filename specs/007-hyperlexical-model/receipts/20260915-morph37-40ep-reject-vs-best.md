# Receipt — morph37 40ep warm morph36 REJECT_VS_BEST

**Date:** 2026-09-15  
**Authority:** Operator continue after morph36 → BEST.  
**BEST:** morph36 (`unbind_exact=0.5455`) — **unchanged** (`promote_best=false`).  
`name_gate=false`. No Hub. No invented OBSERVED gold.

## Recipe

| knob | value |
|------|------:|
| out | `~/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph37` |
| init | **warm** `HYPERLEX_INIT_FROM=...-seed-morph36` |
| epochs | **40** |
| SAVE_BEST_UNBIND | **1** |
| hard atoms | existing only |
| invented OBSERVED? | **No** |

## Gate

| metric | morph36 BEST | morph37 **best** (ep2) | morph37 final |
|--------|-------------:|-----------------------:|--------------:|
| unbind_exact | **0.5455** | **0.5317** | 0.5014 |
| token_f1 | 0.7714 | 0.7682 | — |
| slot_f1 | 0.7714 | 0.7671 | — |
| E2 trunk-forward | PASS | **PASS** | — |

**Verdict: REJECT_VS_BEST** — best 0.5317 < morph36 BEST 0.5455; E2 PASS.  
Warm-start peaked early (ep2); later epochs regressed (final 0.5014).  
Ladder **≥0.55**: still **MISS**.

## Residual themes (best)

`partial_slot_miss=139`, `type_slot_token_miss=70`, `positional_head_filler_miss=24`, `full_miss=14`, `morph_bleed=13`.

## Artifacts

- Spark private: `~/hlx-private/p1-spark-morph37-40ep-warm-morph36-20260915/`
- Workspace: `specs/007-hyperlexical-model/receipts/morph37-40ep-warm-morph36-20260915/`
- Container: `hlx-train-morph37-1789508810` (exit 0)

## Next

- BEST remains morph36. Danny gold still required for OBSERVED `partial_slot_miss` lever.
- Do not invent OBSERVED gold; do not promote without beating morph36.
