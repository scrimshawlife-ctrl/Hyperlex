# morph48 PROMOTE BEST (2026-09-17)

**Authority:** Spec 007. `name_gate=false`.  
**Prior BEST:** morph40 fair n=228 `unbind_exact≈0.7368`. **New BEST:** **morph48**.

## Result

| field | value |
|-------|------:|
| best unbind_exact | **0.7412280701754386** (ep19) |
| fair morph40 | **0.7368421052631579** |
| val n | **228** (unchanged) |
| E2 trunk-forward | **PASS** |
| decision | **PROMOTE_BEST** |

Lever: `HYPERLEX_LAST_TRAINABLE=6` (envelope 4). HEAD_SLOT=2 / HARD=4 / POS=1 held. Warm morph40 + SAVE_BEST; mem 0.3; 40ep.

## Preservation

- morph40 artifacts kept on disk
- morph36 artifacts kept on disk
- Spark `~/.hyperlex/models/BEST` → `...-seed-morph48`

## Ladder

≥0.55 on n=228 remains **HIT** (0.7412).

## Artifacts

- `receipts/morph48-40ep-last6-20260917/`
- Private: `~/hlx-private/p1-spark-morph48-40ep-last6-20260917/`
- Container: `hlx-train-morph48-1789639062`
