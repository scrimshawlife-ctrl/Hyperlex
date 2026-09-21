# morph58 PROMOTE_BEST — observed upsample 3 (2026-09-19)

Container `hlx-train-morph58-1789793254` Exited 0. Gate `morph58-observed-upsample3` finished 2026-09-19T07:14:09Z. `name_gate=false`. No new gold. The 2026-09-19 label packet was not integrated.

## Gate

Same surface as morph56: force 137, hard matched 180, val n=226. `surface_ok=true`.

| | |
|--|--|
| best | **0.8230088495575221** epoch 37 = 186/226 |
| fair morph56 | **0.8185840707964602** = 185/226 |
| decision | **PROMOTE_BEST** (strictly greater, E2 PASS) |
| final epoch 39 | 0.8141592920353983 (184/226) — not the pin |
| only epoch above fair | epoch 37 |

Knob: `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=3` (receipt field `unbind_observed_upsample=3`). Held `HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=2`, LAST=8, HEAD=2, POS=1, TYPE=1, warm init morph56, mem 0.3, 40 epochs, SAVE_BEST.

## E2

`~/hlx/e2-unbind-morph58.json`: `trunk_forward=true`, `e2_pass=true`, `unbind_exact=1.0`, `n_unbind_eval=24`, `n_test=12`, probe `abraxas.recoverable_structure.probe.v0.1`. The train receipt's own `e2_pass` is false because the train job does not run E2. The gate used the separate probe file.

## Pin

`~/.hyperlex/models/BEST` → `hyperlex-encoder-modernbert-base-seed-morph58`. `model.safetensors` present on morph58 and still present on morph56. Residuals on the best epoch: 40 (OBSERVED 30 / INFERRED 10). Themes: `partial_slot_miss` 25, `type_slot_token_miss` 17, `positional_head_filler_miss` 10, `full_miss` 10, `morph_bleed` 2.

Brier null. No Hub.
