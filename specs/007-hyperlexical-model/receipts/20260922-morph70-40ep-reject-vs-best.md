# morph70 REJECT_VS_BEST — role-vocab-filtered new-atoms (2026-09-22)

`name_gate=false`. Exclusive mem 0.3. Qwen stopped+disabled.

## Gate

| | |
|--|--|
| best | **0.9649122807017544** (ep4, 165/171) |
| fair morph65 | **0.9649122807017544** (165/171) |
| decision | **REJECT_VS_BEST** (tie — PIN needs strictly greater) |
| E2 trunk-forward | **PASS** (`unbind_exact=1.0`) |
| container | `hlx-train-morph70-1790092833` exit 0 |
| BEST | stays **morph65** |

## Knob

Settled `local-label-new-atoms` AUTHORIZE filtered to morph65 role vocab (`pos_0..pos_5`) → **force_added=2** (`took an L`, `big W`). 23 longer atoms held. Warm morph65. UPSAMPLE=8 + SECOND_SLOT=2 held. Hang-fix `loop.py`.

## Residuals (best)

n=6. METHOD morph43 AUTHORIZE **0** / ABSTAIN **6** (scaffolding). Do not burn force_added=0.

## Next

Hold BEST morph65. Residual AUTHORIZE=0. Compatible new-atoms exhausted (2 already tried). 23 longer AUTHORIZE atoms still need a **role-vocab expand / non-warm** path — not a force_added=0 warm clone. Upsample frozen; no SECOND_SLOT=4.
