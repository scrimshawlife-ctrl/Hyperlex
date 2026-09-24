# morph71 REJECT_VS_BEST — role-vocab expand / non-warm (2026-09-22)

`name_gate=false`. Exclusive mem 0.3. Qwen stopped+disabled.

## Gate

| | |
|--|--|
| best | **0.9590643274853801** (ep16, 164/171) |
| fair morph65 | **0.9649122807017544** (165/171) |
| decision | **REJECT_VS_BEST** (best < fair) |
| E2 trunk-forward | **PASS** (`unbind_exact=1.0`) |
| container | `hlx-train-morph71-1790110734` exit 0 |
| BEST | stays **morph65** |

## Knob

Role-vocab expand / **non-warm** for 23 held longer `local-label-new-atoms` AUTHORIZE (`pos_6+`; morph65 max `pos_5`). **force_added=23** (194→217) / hard 235→258. No `HYPERLEX_INIT_FROM`. UPSAMPLE=8 + SECOND_SLOT=2 + LAST=8 held. Hang-fix `loop.py`.

## Residuals (best)

n=7 all INFERRED. METHOD morph43 AUTHORIZE **0** / ABSTAIN **7** (scaffolding/wiki/etym). Do not burn force_added=0.

## Next

Hold BEST morph65. Residual AUTHORIZE=0. Longer new-atoms card exhausted (non-warm did not beat fair). Upsample frozen; no SECOND_SLOT=4. No morph72 without a new legal one-knob.
