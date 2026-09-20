# morph60 PROMOTE_BEST — observed upsample 5 (2026-09-19)

Container `hlx-train-morph60-1789829154` Exited 0. Gate `morph60-observed-upsample5` finished 2026-09-19T18:04:45Z. `name_gate=false`. No new gold. The 2026-09-19 label packet was not integrated.

## Gate

Same surface as morph59: force 137, hard matched 180, val n=226. `surface_ok=true`.

| | |
|--|--|
| best | **0.8407079646017699** epoch 9 = 190/226 |
| fair morph59 | **0.831858407079646** = 188/226 |
| decision | **PROMOTE_BEST** (strictly greater, E2 PASS) |
| tied fair, not a pin | epoch 12 and epoch 35 |
| final epoch 39 | 0.8230088495575221 (186/226) — not the pin |

Knob: `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=5` (receipt field `unbind_observed_upsample=5`). Held `HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=2`, LAST=8, HEAD=2, POS=1, TYPE=1, warm init morph59, mem 0.3, 40 epochs, SAVE_BEST.

## E2

`~/hlx/e2-unbind-morph60.json`: `trunk_forward=true`, `e2_pass=true`, `unbind_exact=1.0`, `n_unbind_eval=24`, `n_test=12`, probe `abraxas.recoverable_structure.probe.v0.1`. The train receipt's own `e2_pass` is false because the train job does not run E2. The gate used the separate probe file.

## Pin

`~/.hyperlex/models/BEST` → `hyperlex-encoder-modernbert-base-seed-morph60`. `model.safetensors` present on morph60 and still present on morph59. Residuals on the best epoch: 36 (OBSERVED 26 / INFERRED 10). Themes: `partial_slot_miss` 23, `type_slot_token_miss` 17, `full_miss` 10, `positional_head_filler_miss` 7, `morph_bleed` 2.

Brier null. No Hub.
