# morph66 REJECT_VS_BEST — residual gold force/hard (2026-09-21)

Container `hlx-train-morph66-1789969749` Exited 0. Gate `morph66-residual-gold` finished 2026-09-21T10:21:40Z. `name_gate=false`.

## Gate

Same surface as fair-eval morph65 on expanded force: force keys 164 (matched 162), hard 206→202 matched, val n=201. `surface_ok=true`.

| | |
|--|--|
| best | **0.9502487562189055** epoch 9 = 191/201 |
| fair morph65 | **0.9601990049751243** = 193/201 |
| decision | **REJECT_VS_BEST** (strictly less; E2 PASS) |
| also tied best | epochs 15, 20 |
| BEST stays | **seed-morph65** |

Knob: force/hard morph63 residual gold (`force_train_morph66_expanded.jsonl` / `hard_atoms_train_morph66.jsonl`). Held `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=8`, `HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=2`, warm init morph65, LAST=8, HEAD=2, POS=1, TYPE=1, HARD_UPSAMPLE=4, mem **0.3 exclusive**, 40 epochs, SAVE_BEST. Upsample ladder frozen. Qwen stayed stopped+disabled.

## E2

`~/hlx/e2-unbind-morph66.json`: `trunk_forward=true`, `e2_pass=true`, `unbind_exact=1.0`, `n_unbind_eval=24`, `n_test=12`.

## Pin

BEST symlink unchanged → `hyperlex-encoder-modernbert-base-seed-morph65`. morph66 weights kept on disk (not BEST). Residuals on best epoch: **10** (OBSERVED 1 / INFERRED 9). Themes: `partial_slot_miss` 10, `type_slot_token_miss` 6. Schemes: type_slot 7 / positional 3.

Gold force-train did not beat prior BEST on the same post-force surface. Do not replay the same force/hard packet.

Brier null. No Hub.
