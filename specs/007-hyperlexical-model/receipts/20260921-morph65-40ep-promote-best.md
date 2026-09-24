# morph65 PROMOTE_BEST — observed upsample 10 (2026-09-21)

Container `hlx-train-morph65-1789947808` Exited 0. Gate `morph65-observed-upsample10` finished 2026-09-21T05:28:01Z. `name_gate=false`. No new gold during this run (label packet + residual gold prepared offline for morph66).

## Gate

Same surface as morph63/64: force 137, hard matched 180, val n=226. `surface_ok=true`.

| | |
|--|--|
| best | **0.8584070796460177** epoch 6 = 194/226 |
| fair morph63 | **0.8539823008849557** = 193/226 |
| decision | **PROMOTE_BEST** (strictly greater, E2 PASS) |
| BEST → | **seed-morph65** |

Knob: `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=10`. Held `HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=2`, LAST=8, HEAD=2, POS=1, TYPE=1, warm init morph63, mem **0.3 exclusive**, 40 epochs, SAVE_BEST. Qwen stayed stopped+disabled.

## E2

`~/hlx/e2-unbind-morph65.json`: `trunk_forward=true`, `e2_pass=true`, `unbind_exact=1.0`, `n_unbind_eval=24`, `n_test=12`.

## Pin

`~/.hyperlex/models/BEST` → `hyperlex-encoder-modernbert-base-seed-morph65`. morph63 + morph62 preserved on disk. Residuals on best epoch themes: `partial_slot_miss` 20, `type_slot_token_miss` 15, `full_miss` 8, `positional_head_filler_miss` 8, `morph_bleed` 1.

Upsample ladder gain this step: **+1 exact** (193→194). Ladder: 3/4/5=+2; 6/7/8=+1; 9=+0 tie; **10=+1**. Freeze ladder — do not run upsample 11+.

Brier null. No Hub.
