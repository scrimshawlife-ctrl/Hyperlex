# morph59 PROMOTE_BEST — observed upsample 4 (2026-09-19)

Container `hlx-train-morph59-1789803430` Exited 0. Gate `morph59-observed-upsample4` finished 2026-09-19T10:16:05Z. `name_gate=false`. No new gold. The 2026-09-19 label packet was not integrated.

## Gate

Same surface as morph58: force 137, hard matched 180, val n=226. `surface_ok=true`.

| | |
|--|--|
| best | **0.831858407079646** epoch 14 = 188/226 |
| fair morph58 | **0.8230088495575221** = 186/226 |
| decision | **PROMOTE_BEST** (strictly greater, E2 PASS) |
| also tied the best | epoch 30 and epoch 33 |
| final epoch 39 | 0.8230088495575221 (186/226) — not the pin |

Knob: `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=4` (receipt field `unbind_observed_upsample=4`). Held `HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=2`, LAST=8, HEAD=2, POS=1, TYPE=1, warm init morph58, mem 0.3, 40 epochs, SAVE_BEST.

## E2

`~/hlx/e2-unbind-morph59.json`: `trunk_forward=true`, `e2_pass=true`, `unbind_exact=1.0`, `n_unbind_eval=24`, `n_test=12`, probe `abraxas.recoverable_structure.probe.v0.1`. The train receipt's own `e2_pass` is false because the train job does not run E2. The gate used the separate probe file.

## Pin

`~/.hyperlex/models/BEST` → `hyperlex-encoder-modernbert-base-seed-morph59`. `model.safetensors` present on morph59 and still present on morph58. Residuals on the best epoch: 38 (OBSERVED 28 / INFERRED 10). Themes: `partial_slot_miss` 23, `type_slot_token_miss` 17, `positional_head_filler_miss` 10, `full_miss` 9, `morph_bleed` 3.

Brier null. No Hub.
