# morph57 REJECT_VS_BEST — second-slot weight 3 tie (2026-09-19)

Container `hlx-train-morph57-1789775196` Exited 0. Gate `morph57-second-slot3` finished 2026-09-19T01:50:56Z. `name_gate=false`. No new gold.

Same surface as morph56: force 137, val n=226, `surface_ok=true`. Knob `HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=3` (`unbind_second_slot_weight=3.0`). Warm init morph56. LAST=8, HEAD=2, POS=1, TYPE=1, mem 0.3, 40ep, SAVE_BEST.

| | |
|--|--|
| best | **0.8185840707964602** epoch 34 = 185/226 |
| fair morph56 | **0.8185840707964602** = 185/226 |
| decision | **REJECT_VS_BEST** (tie is not a promote) |
| final epoch 39 | 0.8008849557522124 |
| also | ep22/33/38 0.8141592920353983 (184/226) |

E2 `~/hlx/e2-unbind-morph57.json`: `trunk_forward=true`, `e2_pass=true`, `unbind_exact=1.0`, `n_unbind_eval=24`.

`~/.hyperlex/models/BEST` remains `hyperlex-encoder-modernbert-base-seed-morph56`. morph56 and morph57 `model.safetensors` both on disk.

Brier null. No Hub.
