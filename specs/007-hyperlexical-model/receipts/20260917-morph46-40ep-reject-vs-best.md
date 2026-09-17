# morph46 REJECT_VS_BEST (2026-09-17)

**Authority:** Spec 007. `name_gate=false`.  
**BEST held:** morph40 fair n=228 `unbind_exact≈0.7368`.

## Result

| field | value |
|-------|------:|
| best unbind_exact | **0.7149122807017544** (ep2) |
| fair morph40 | **0.7368421052631579** |
| val n | **228** (unchanged) |
| decision | **REJECT_VS_BEST** |

Lever: `HARD_UPSAMPLE=6` (was 4). HEAD_SLOT held at 2. Warm morph40 + SAVE_BEST; mem 0.3; 40ep. Container `hlx-train-morph46-1789626971` exit 0.

Residual themes still `partial_slot_miss` / `positional_head_filler_miss` / `type_slot_token_miss`. Harder mix hurt vs morph40 and vs morph45.

## Coordination

Train launched by `bc-f84803c9` (`hlx-train-morph46-1789626971`). Gate docs first landed by `bc-3e55c42d`; E2 + package pin completed by train owner (`e2_pass=True`, `unbind_exact=1.0`).

## Next

Recipe lever still open per escalate (curriculum / LR / last-N). HEAD_SLOT=3 and HARD=6 tried. Do **not** repeat warm+force residual-gold clones. See morph47.
