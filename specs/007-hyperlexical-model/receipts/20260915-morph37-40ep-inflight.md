# Receipt — morph37 40ep IN FLIGHT (warm morph36 BEST)

**Date:** 2026-09-15  
**Authority:** Operator continue after morph36 → BEST.  
**BEST:** morph36 (`unbind_exact=0.5455`) — do **not** clobber mid-train.  
`name_gate=false`. No Hub. No invented OBSERVED gold.

## Recipe

| knob | value |
|------|------:|
| out | `~/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph37` (**new**) |
| init | **warm** `HYPERLEX_INIT_FROM=...-seed-morph36` (BEST primary = best ep23) |
| epochs / batch / lr / last_n | **40** / 8 / 2e-5 / 4 |
| primary | `slot_ce` |
| HEAD_SLOT | 2 |
| OBSERVED / HARD upsample | 2 / 4 |
| hard atoms | existing `~/hlx/hard_atoms_train.jsonl` only |
| **SAVE_BEST_UNBIND** | **1** |
| invented OBSERVED gold? | **No** |

## Gate plan

Compare primary (best-saved) vs morph36 BEST **0.5455**.  
May promote morph37 → BEST if exact ≥ morph36 best (operator continue-authority).  
Clear ladder mark if ≥ **0.55**.  
Do not invent Danny OBSERVED gold.

## Container

`hlx-train-morph37-1789508810`
