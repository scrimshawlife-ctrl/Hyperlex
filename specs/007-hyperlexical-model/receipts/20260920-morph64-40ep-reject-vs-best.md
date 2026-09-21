# morph64 REJECT_VS_BEST — observed upsample 9 (2026-09-20)

Container `hlx-train-morph64-1789928581` Exited 0. Gate `morph64-observed-upsample9` finished 2026-09-20T23:27:33Z. `name_gate=false`. No new gold. The 2026-09-19 label packet was not integrated.

## Gate

Same surface as morph63: force 137, hard matched 180, val n=226. `surface_ok=true`.

| | |
|--|--|
| best | **0.8539823008849557** epoch 28 = 193/226 |
| fair morph63 | **0.8539823008849557** = 193/226 |
| decision | **REJECT_VS_BEST** (tie is not a pin; E2 PASS) |
| also tied fair | epoch 34 |
| BEST stays | **seed-morph63** |

Knob: `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=9`. Held `HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=2`, LAST=8, HEAD=2, POS=1, TYPE=1, warm init morph63, mem **0.3 exclusive**, 40 epochs, SAVE_BEST. Qwen stayed stopped+disabled.

## E2

`~/hlx/e2-unbind-morph64.json`: `trunk_forward=true`, `e2_pass=true`, `unbind_exact=1.0`, `n_unbind_eval=24`, `n_test=12`.

## Pin

BEST symlink unchanged → `hyperlex-encoder-modernbert-base-seed-morph63`. morph64 weights kept on disk (not BEST). Residuals on the best epoch: 33 (OBSERVED 26 / INFERRED 7). Themes: `partial_slot_miss` 20, `type_slot_token_miss` 16, `full_miss` 9, `positional_head_filler_miss` 8, `morph_bleed` 2.

Upsample ladder gain this step: **+0 exact** (tie). Prior 6/7/8 were +1; 3/4/5 were +2. Ladder flat here.

Brier null. No Hub.
