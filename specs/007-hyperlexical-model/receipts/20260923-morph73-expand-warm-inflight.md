# morph73 IN FLIGHT — INIT_EXPAND_VOCAB=1 warm morph65 (2026-09-23)

**Authority:** operator handle-the-knob-first-and-continue 2026-09-23 after morph72 REJECT.

## One knob

`HYPERLEX_INIT_EXPAND_VOCAB=1` + `HYPERLEX_INIT_FROM=seed-morph65` (warm-expand).

Warm morph65 was blocked after morph71 harvest added `pos_6`/`pos_7` (+ new fillers). Expand remap copies overlapping role/filler rows by name; new vocab rows stay at init. Default fail-closed mismatch preserved when env unset.

## Held

| knob | value |
|------|-------|
| force/hard | morph72 = morph71 (217/258); force_added=0 |
| UPSAMPLE | 10 (morph72 / BEST envelope) |
| SECOND_SLOT | 2 |
| LAST_TRAINABLE | 8 |
| SAVE_BEST | 1 |
| mem_fraction | 0.3 exclusive |
| epochs / lr / batch | 40 / 2e-5 / 8 |

## Gate

Same-surface fair: morph65 BEST on morph73 force = **0.9649122807017544** n=171. Promote iff best > fair and E2 trunk-forward unbind_exact=1.0.

## Live

| field | value |
|-------|-------|
| container | `hlx-train-morph73-1790148566` |
| fair | 0.9649122807017544 n=171 |
| loop.md5 | `75f63a7d272ed7c8f7d430f4d9439b8b` |

## Freeze

Upsample 11+ frozen. No SECOND_SLOT=4. Qwen stays stopped.

## Private

`~/hlx-private/p1-spark-morph73-expand-warm-20260923` + `~/hlx-private/p1-spark-morph73-40ep-expand-warm-20260923`
