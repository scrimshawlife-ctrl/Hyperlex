# Receipt — morph38 40ep IN FLIGHT (warm morph36, LR 1e-5)

**Date:** 2026-09-15  
**Authority:** Operator continue after morph37 REJECT_VS_BEST. Promote where earned.  
**BEST:** morph36 (`unbind_exact=0.5455`) — do **not** clobber mid-train.  
`name_gate=false`. No Hub. No invented OBSERVED gold.

## Lever vs morph37 (one change)

| knob | morph37 | **morph38** |
|------|--------:|------------:|
| `HYPERLEX_TRAIN_LR` | **2e-5** | **1e-5** |

**Justification:** morph37 warm from morph36 peaked at **ep2** (0.5317) then regressed (final 0.5014). Same cold-start LR under warm continue overshoots early. Halve LR; hold all other envelope knobs.

## Recipe

| knob | value |
|------|------:|
| out | `~/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph38` (**new**) |
| init | **warm** `HYPERLEX_INIT_FROM=...-seed-morph36` (BEST primary) |
| epochs / batch / **lr** / last_n | **40** / 8 / **1e-5** / 4 |
| primary | `slot_ce` |
| HEAD_SLOT | 2 |
| OBSERVED / HARD upsample | 2 / 4 |
| hard atoms | existing `~/hlx/hard_atoms_train.jsonl` only |
| **SAVE_BEST_UNBIND** | **1** |
| invented OBSERVED gold? | **No** |

## Gate plan

Compare primary (best-saved) vs morph36 BEST **0.5455**.  
If exact **> 0.5455** → promote morph38 → BEST (authority granted); preserve morph36 dir.  
If ≥ **0.55** → note ladder cleared.  
If ≤ BEST → **REJECT_VS_BEST**, no promote.  
Do not invent Danny OBSERVED gold.

## Container

`hlx-train-morph38-1789514700`
