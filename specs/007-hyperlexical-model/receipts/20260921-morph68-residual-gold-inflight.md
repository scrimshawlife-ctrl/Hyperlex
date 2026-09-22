# morph68 INFLIGHT — residual gold force/hard (2026-09-21)

`name_gate=false`. Exclusive mem 0.3. Qwen stopped+disabled.

## One knob

METHOD morph43 AUTHORIZE on morph67 residuals (n=2) → force/hard expand + harvest OBSERVED append.
Force **166** / hard **208**. Warm morph65. UPSAMPLE=8 + SECOND_SLOT=2 held.

## Fair (morph65 on morph68 surface)

| | |
|--|--|
| exact | **0.9695431472081218** (191/197) |
| path | `~/hlx/fair-eval-morph65-morph68.json` |

## Recipe (held except force/hard)

| knob | value |
|--|--|
| warm | morph65 |
| UPSAMPLE | 8 (held) |
| SECOND_SLOT | 2 (held) |
| LAST | 8 |
| HEAD_SLOT | 2 |
| HARD_UPSAMPLE | 4 |
| LR | 2e-5 |
| epochs | 40 |
| SAVE_BEST | on |
| PIN | best > fair 0.9695 on n=197 **and** E2 trunk-forward exact 1.0 |

## Not this card

upsample 11+ · SECOND_SLOT=4 · invent OBSERVED fillers · Hub · name_gate · replay morph67 SoT without new gold

Private: `~/hlx-private/p1-spark-morph68-40ep-residual-gold-20260921/`

## Hang + fix relaunch

1. `hlx-train-morph68-1790029975` **hung** after ep4 best **0.964467** (~3h, 98% CPU, GPU util 0, mem held). Aside `*.hung-ep4-20260922T013202Z`.
2. Blind relaunch `hlx-train-morph68-1790040737` same hang (~75m). Aside `*.hung-ep4-relaunch-20260922T031305Z`.
3. **Root cause:** per-step `loss.detach().cpu()` (~12k CUDA host syncs/epoch) + SAVE_BEST full encoder GPU→CPU copy → post-ep4 host spin. Not CPU device fallback.
4. **Fix in `scripts/shadow/hyperlexical/loop.py`:** on-device `last_train_loss` (one `.item()`/epoch); `cuda.synchronize` + `empty_cache` after SAVE_BEST; `epoch-progress.jsonl` + stdout flush. Relaunch `PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512` (no `expandable_segments`).
5. **In flight:** `hlx-train-morph68-1790047095` — same one-knob. Receipts: `HANG_*.json`, `HANG_FIX_20260922T0315Z.json`.
