# morph62 PROMOTE_BEST — observed upsample 7 (2026-09-20)

Container `hlx-train-morph62-1789896471` Exited 0. Gate `morph62-observed-upsample7` finished 2026-09-20T13:28:20Z. `name_gate=false`. No new gold. The 2026-09-19 label packet was not integrated.

## Gate

Same surface as morph61: force 137, hard matched 180, val n=226. `surface_ok=true`.

| | |
|--|--|
| best | **0.8495575221238938** epoch 21 = 192/226 |
| fair morph61 | **0.8451327433628318** = 191/226 |
| decision | **PROMOTE_BEST** (strictly greater, E2 PASS) |
| also beat fair | epoch 27 (tied best) |
| tied fair, not a pin | epochs 23, 33, 38 |
| final epoch 39 | 0.8407079646017699 (190/226) — not the pin |

Knob: `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=7` (receipt field). Held `HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=2`, LAST=8, HEAD=2, POS=1, TYPE=1, warm init morph61, mem **0.3 exclusive**, 40 epochs, SAVE_BEST. Qwen stayed stopped+disabled.

## E2

`~/hlx/e2-unbind-morph62.json`: `trunk_forward=true`, `e2_pass=true`, `unbind_exact=1.0`, `n_unbind_eval=24`, `n_test=12`, probe `abraxas.recoverable_structure.probe.v0.1`.

## Pin

`~/.hyperlex/models/BEST` → `hyperlex-encoder-modernbert-base-seed-morph62`. `model.safetensors` present on morph62; morph61 + morph60 preserved. Residuals on the best epoch: 34 (OBSERVED 26 / INFERRED 8). Themes: `partial_slot_miss` 21, `type_slot_token_miss` 14, `positional_head_filler_miss` 9, `full_miss` 8, `morph_bleed` 1.

Upsample ladder gain this step: **+1 exact** (191→192). Same step size as upsample 6. Prior steps 3/4/5 were +2 each. Diminishing.

Brier null. No Hub.
