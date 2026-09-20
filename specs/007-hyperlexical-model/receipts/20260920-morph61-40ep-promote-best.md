# morph61 PROMOTE_BEST — observed upsample 6 (2026-09-20)

Container `hlx-train-morph61-1789880707` Exited 0. Gate `morph61-observed-upsample6` finished 2026-09-20T08:27:37Z. `name_gate=false`. No new gold. The 2026-09-19 label packet was not integrated.

## Gate

Same surface as morph60: force 137, hard matched 180, val n=226. `surface_ok=true`.

| | |
|--|--|
| best | **0.8451327433628318** epoch 26 = 191/226 |
| fair morph60 | **0.8407079646017699** = 190/226 |
| decision | **PROMOTE_BEST** (strictly greater, E2 PASS) |
| tied fair, not a pin | epochs 2, 3, 28 |
| final epoch 39 | 0.8185840707964602 (185/226) — not the pin |

Knob: `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=6` (receipt field `unbind_observed_upsample=6`). Held `HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=2`, LAST=8, HEAD=2, POS=1, TYPE=1, warm init morph60, mem **0.3 exclusive**, 40 epochs, SAVE_BEST.

## Spark note

First launch OOM'd beside `qwen38-27b`. Operator killed Qwen; systemd unit was stopped and disabled. Exclusive remount `hlx-train-morph61-1789880707`.

## E2

`~/hlx/e2-unbind-morph61.json`: `trunk_forward=true`, `e2_pass=true`, `unbind_exact=1.0`, `n_unbind_eval=24`, `n_test=12`, probe `abraxas.recoverable_structure.probe.v0.1`. The train receipt's own `e2_pass` is false because the train job does not run E2. The gate used the separate probe file.

## Pin

`~/.hyperlex/models/BEST` → `hyperlex-encoder-modernbert-base-seed-morph61`. `model.safetensors` present on morph61 and still present on morph60. Residuals on the best epoch: 35 (OBSERVED 25 / INFERRED 10). Themes: `partial_slot_miss` 21, `type_slot_token_miss` 15, `full_miss` 9, `positional_head_filler_miss` 9, `morph_bleed` 1.

Upsample ladder gain this step: **+1 exact** (190→191). Prior steps 3/4/5 were +2 each. Diminishing.

Brier null. No Hub.
