# morph73 REJECT_VS_BEST — INIT_EXPAND_VOCAB warm morph65 (2026-09-23)

`name_gate=false`. Exclusive mem 0.3. Qwen stopped+disabled.

## Gate

| | |
|--|--|
| best | **0.9649122807017544** (ep10, 165/171) |
| fair morph65 | **0.9649122807017544** (165/171) |
| decision | **REJECT_VS_BEST** (best == fair; tie ≠ promote) |
| E2 trunk-forward | **PASS** (`unbind_exact=1.0`) |
| container | `hlx-train-morph73-1790148566` exit 0 |
| BEST | stays **morph65** |

## Knob

`HYPERLEX_INIT_EXPAND_VOCAB=1` + `HYPERLEX_INIT_FROM=seed-morph65` (warm-expand). Expand applied: roles mapped 10/10 (+2 new), fillers mapped 1980/1980 (+26 new). Same morph72=morph71 force/hard **217/258** (force_added=0). UPSAMPLE=10 / SECOND_SLOT=2 / LAST=8 held. Hang-fix `loop.py`.

Note: peak **ties** fair — expand-warm recovered to morph65 exact but did not exceed. Strictly greater required.

## Residuals (best)

n=6 all INFERRED (2 positional / 4 type_slot). METHOD morph43 AUTHORIZE **0** / ABSTAIN **6** (scaffolding/wiki/etym). Do not burn force_added=0 / fair-tie / identical expand-warm replay.

## Next

Hold BEST morph65. Residual AUTHORIZE=0. Upsample freeze remains **11+**. No SECOND_SLOT=4. No morph74 without a new legal one-knob.
