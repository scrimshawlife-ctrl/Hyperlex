# morph63 PROMOTE_BEST — observed upsample 8 (2026-09-20)

Container `hlx-train-morph63-1789911656` Exited 0. Gate `morph63-observed-upsample8` finished 2026-09-20T17:57:27Z. `name_gate=false`. No new gold. The 2026-09-19 label packet was not integrated.

## Gate

Same surface as morph62: force 137, hard matched 180, val n=226. `surface_ok=true`.

| | |
|--|--|
| best | **0.8539823008849557** epoch 13 = 193/226 |
| fair morph62 | **0.8495575221238938** = 192/226 |
| decision | **PROMOTE_BEST** (strictly greater, E2 PASS) |
| also beat fair | epochs 17, 21 (tied best) |
| tied fair, not a pin | epochs 9, 15, 18, 20, 23, 29, 33 |
| final epoch 39 | below pin — SAVE_BEST kept ep13 |

Knob: `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=8` (receipt field). Held `HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=2`, LAST=8, HEAD=2, POS=1, TYPE=1, warm init morph62, mem **0.3 exclusive**, 40 epochs, SAVE_BEST. Qwen stayed stopped+disabled.

## E2

`~/hlx/e2-unbind-morph63.json`: `trunk_forward=true`, `e2_pass=true`, `unbind_exact=1.0`, `n_unbind_eval=24`, `n_test=12`, probe `abraxas.recoverable_structure.probe.v0.1`.

## Pin

`~/.hyperlex/models/BEST` → `hyperlex-encoder-modernbert-base-seed-morph63`. `model.safetensors` present on morph63; morph62 + morph61 preserved. Residuals on the best epoch: 33 (OBSERVED 25 / INFERRED 8). Themes: `partial_slot_miss` 20, `type_slot_token_miss` 15, `positional_head_filler_miss` 9, `full_miss` 8.

Upsample ladder gain this step: **+1 exact** (192→193). Same step size as upsample 6/7. Prior steps 3/4/5 were +2 each. Diminishing.

Brier null. No Hub.
