# morph50 PROMOTE BEST (2026-09-18)

**Authority:** Spec 007. `name_gate=false`.  
**Prior BEST:** morph49 fair n=226 `unbind_exact≈0.7920` (recomputed after +2 gold). **New BEST:** **morph50**.

## Result

| field | value |
|-------|------:|
| best unbind_exact | **0.8097345132743363** (ep38) |
| fair morph49 | **0.7920353982300885** |
| val n | **226** |
| E2 trunk-forward | **PASS** (1.0) |
| decision | **PROMOTE_BEST** |

Lever: `HYPERLEX_LAST_TRAINABLE=8` (MAX; was 7) +2 METHOD morph49 residual gold. HEAD_SLOT=2 / HARD=4 / POS=1 held. Warm morph49 + SAVE_BEST; mem 0.3; 40ep.

## Gold delta

| item | before → after |
|------|----------------|
| morph49 residuals | n=49 · authorize **39** / abstain **10** |
| new train-ready | **+2** (`TOKEN:jailbreak SLOT:prompt`, `boon coon` SoT flip) |
| force-train | **135 → 137** |
| hard_atoms | **180 → 182** (matched 180 at train) |
| fair surface | n=228 → **n=226**; fair morph49 **0.7851 → 0.7920** |

## Preservation

- morph49 + morph48 + morph40 + morph36 artifacts kept on disk
- Spark `~/.hyperlex/models/BEST` → `...-seed-morph50`
- Single pin via `GATE_LOCK.json` (owner `coordinate-continue-training`; sibling `bc-b4ecc915-ddac-5aaa-9cce-e29d15c18061`)

## Ladder

≥0.55 on civilian unbind remains **HIT** (0.8097).

## Artifacts

- `receipts/morph50-40ep-last8-20260918/`
- Private: `~/hlx-private/p1-spark-morph50-40ep-last8-20260918/`
- Container: `hlx-train-morph50-1789703143`
