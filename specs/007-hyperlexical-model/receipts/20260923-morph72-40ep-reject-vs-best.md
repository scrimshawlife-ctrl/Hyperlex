# morph72 REJECT_VS_BEST — UPSAMPLE=10 non-warm (2026-09-23)

`name_gate=false`. Exclusive mem 0.3. Qwen stopped+disabled.

## Gate

| | |
|--|--|
| best | **0.9532163742690059** (ep22, 163/171) |
| fair morph65 | **0.9649122807017544** (165/171) |
| decision | **REJECT_VS_BEST** (best < fair) |
| E2 trunk-forward | **PASS** (`unbind_exact=1.0`) |
| container | `hlx-train-morph72-1790129677` exit 0 |
| BEST | stays **morph65** |

## Knob

`HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=10` (was 8 on morph71; BEST morph65 envelope). Same morph71 force/hard **217/258**. Non-warm. SECOND_SLOT=2 / LAST=8 held.

Note: peak **below** morph71's 0.9591 (UPSAMPLE=8 non-warm) — UPSAMPLE=10 did not help on this surface.

## Residuals (best)

n=8 all INFERRED. METHOD morph43 AUTHORIZE **0** / ABSTAIN **8**. Do not burn force_added=0 / identical UPSAMPLE=10 replay.

## Next

Hold BEST morph65. Residual AUTHORIZE=0. Upsample freeze remains **11+**. No SECOND_SLOT=4. No morph73 without a new legal one-knob.
