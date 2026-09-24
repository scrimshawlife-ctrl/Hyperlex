# morph67 REJECT_VS_BEST — SoT flip (2026-09-21)

Container `hlx-train-morph67-1790010500` Exited 0. Gate `morph67-sot-flip` finished 2026-09-21T22:15:32Z. `name_gate=false`.

## Gate

Same surface as fair-eval morph65 after SoT flip: force keys 164 moved 164, val n=199. `surface_ok=true`.

| | |
|--|--|
| best | **0.9597989949748744** epoch 18 = 191/199 |
| fair morph65 | **0.9698492462311558** = 193/199 |
| decision | **REJECT_VS_BEST** (strictly less; E2 PASS) |
| BEST stays | **seed-morph65** |

Knob: SoT INFERRED→OBSERVED for 2 METHOD AUTHORIZE morph65 force residuals (harvest sidecar). Held force/hard morph66 paths, `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=8`, `HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=2`, warm init morph65, LAST=8, HEAD=2, POS=1, TYPE=1, HARD_UPSAMPLE=4, mem **0.3 exclusive**, 40 epochs, SAVE_BEST. Upsample ladder frozen. Qwen stayed stopped+disabled.

## E2

`~/hlx/e2-unbind-morph67.json`: `trunk_forward=true`, `e2_pass=true`, `unbind_exact=1.0`, `n_unbind_eval=24`, `n_test=12`.

## Pin

BEST symlink unchanged → `hyperlex-encoder-modernbert-base-seed-morph65`. morph67 weights kept on disk (not BEST). Residuals on best epoch: **8** (OBSERVED 1 / INFERRED 7). Themes: `partial_slot_miss` 6, `positional_head_filler_miss` 2, `type_slot_token_miss` 3. Schemes: type_slot 4 / positional 4.

SoT flip raised the fair bar (same 193 correct on n=199) but train best stayed below. Do not replay the same SoT flip / identical force surface.

Brier null. No Hub.

Private: `~/hlx-private/p1-spark-morph67-40ep-sot-flip-20260921/`
Receipts: `receipts/morph67-sot-flip-20260921/`
