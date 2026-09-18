# morph49 PROMOTE BEST (2026-09-18)

**Authority:** Spec 007. `name_gate=false`.  
**Prior BEST:** morph48 fair n=228 `unbind_exact≈0.7412`. **New BEST:** **morph49**.

## Result

| field | value |
|-------|------:|
| best unbind_exact | **0.7850877192982456** (ep27) |
| fair morph48 | **0.7412280701754386** |
| val n | **228** (unchanged) |
| E2 trunk-forward | **PASS** |
| decision | **PROMOTE_BEST** |

Lever: `HYPERLEX_LAST_TRAINABLE=7` (was 6). HEAD_SLOT=2 / HARD=4 / POS=1 held. Warm morph48 + SAVE_BEST; mem 0.3; 40ep.

## Preservation

- morph48 artifacts kept on disk
- morph40 + morph36 artifacts kept on disk
- Spark `~/.hyperlex/models/BEST` → `...-seed-morph49`
- Single pin via `GATE_LOCK.json` (owner `bc-ad3024d5-f1c6-5e5a-8c5e-757ca53e37d1`)

## Ladder

≥0.55 on n=228 remains **HIT** (0.7851).

## Artifacts

- `receipts/morph49-40ep-last7-20260917/`
- Private: `~/hlx-private/p1-spark-morph49-40ep-last7-20260917/`
- Container: `hlx-train-morph49-1789694077`
