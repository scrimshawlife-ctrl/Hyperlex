# Receipt — morph38 40ep warm morph36 LR 1e-5 REJECT_VS_BEST

**Date:** 2026-09-15  
**Authority:** Operator continue after morph37 REJECT_VS_BEST. Promote where earned.  
**BEST:** morph36 (`unbind_exact=0.5455`) — **unchanged** (`promote_best=false`).  
`name_gate=false`. No Hub. No invented OBSERVED gold.

## Lever vs morph37 (one change)

| knob | morph37 | **morph38** |
|------|--------:|------------:|
| `HYPERLEX_TRAIN_LR` | **2e-5** | **1e-5** |

**Justification:** morph37 warm peaked ep2 then regressed under cold-start LR. Halve LR for warm continue.

## Recipe

| knob | value |
|------|------:|
| out | `~/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph38` |
| init | **warm** `HYPERLEX_INIT_FROM=...-seed-morph36` |
| epochs / batch / **lr** / last_n | **40** / 8 / **1e-5** / 4 |
| SAVE_BEST_UNBIND | **1** |
| hard atoms | existing only |
| invented OBSERVED? | **No** |

## Gate

| metric | morph36 BEST | morph38 **best** (ep2) | morph38 final |
|--------|-------------:|-----------------------:|--------------:|
| unbind_exact | **0.5455** | **0.5234** | 0.4656 |
| token_f1 | 0.7714 | 0.7660 | — |
| slot_f1 | 0.7714 | 0.7660 | — |
| E2 trunk-forward | PASS | **PASS** | — |

**Verdict: REJECT_VS_BEST** — best 0.5234 < morph36 BEST 0.5455; E2 PASS.  
Warm LR 1e-5 still peaked early (ep2) and regressed (final 0.4656); early peak also below morph37's 0.5317.  
Ladder **≥0.55**: still **MISS**.

## Residual themes (best)

`partial_slot_miss=140`, `type_slot_token_miss=70`, `positional_head_filler_miss=26`, `full_miss=14`, `morph_bleed=14`.

## Artifacts

- Spark private: `~/hlx-private/p1-spark-morph38-40ep-warm-morph36-lr1e5-20260915/`
- Workspace: `specs/007-hyperlexical-model/receipts/morph38-40ep-warm-morph36-lr1e5-20260915/`
- Container: `hlx-train-morph38-1789514700` (exit 0)

## Next

- BEST remains morph36. Waiting on Danny gold for OBSERVED `partial_slot_miss` lever.
- Ladder 0.55 MISS. Warm envelope ± LR did not clear; next climb needs a **non-LR** lever (or Danny gold) — do not invent OBSERVED.
- Do not promote without beating morph36.
