# morph56 PROMOTE_BEST — second-slot weight 2 (2026-09-18)

Container `hlx-train-morph56-1789766977` Exited 0. Gate `morph56-second-slot2` finished 2026-09-18T23:25:59Z. `name_gate=false`. No new gold.

## Gate

Same surface as the morph50 pin (force 137, val n=226). `surface_ok=true`.

| | |
|--|--|
| best | **0.8185840707964602** epoch 10 = 185/226 |
| fair morph50 | **0.8097345132743363** = 183/226 |
| decision | **PROMOTE_BEST** (strictly greater, E2 PASS) |
| final epoch 39 | 0.7964601769911505 — not the pin |
| also | ep2 0.8141592920353983 (184/226); ep14 tied the old fair |

Knob: `HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=2` (receipt field `unbind_second_slot_weight=2.0`). Held LAST=8, HEAD=2, POS=1, TYPE=1, warm init morph50, mem 0.3, 40 epochs, SAVE_BEST. Hard atoms matched 180 on `hard_atoms_train_morph50.jsonl`.

## E2

`~/hlx/e2-unbind-morph56.json`: `trunk_forward=true`, `e2_pass=true`, `unbind_exact=1.0`, `n_unbind_eval=24`, `n_test=12`, probe `abraxas.recoverable_structure.probe.v0.1`. The train receipt's own `e2_pass` is false because the train job does not run E2. The gate used the separate probe file.

## Pin

`~/.hyperlex/models/BEST` → `hyperlex-encoder-modernbert-base-seed-morph56`. `model.safetensors` present on morph56 and still present on morph50. Residuals on the best epoch: 41 (OBSERVED 31 / INFERRED 10).

Brier null. No Hub.
