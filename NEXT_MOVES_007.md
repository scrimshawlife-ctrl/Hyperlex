# Spec 007 — next card: OBSERVED upsample 7; BEST=morph61

`name_gate=false`. morph61 observed upsample 6 beat fair morph60 by one exact. Do not replay upsample 6. Do not run second-slot weight 4. Do not add gold.

## One knob

`HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=7` (6 just promoted; not stacked with another lever). Residuals on the pin are 35, of which 25 are OBSERVED (`partial_slot_miss` 21).

Hold from morph61: warm morph61, `SECOND_SLOT=2`, LR=2e-5, LAST=8, HEAD=2, POS=1, TYPE=1, HARD=4, force 137, mem 0.3 exclusive, 40ep, SAVE_BEST.

| | |
|--|--|
| fair | **0.8451327433628318** n=226 (191/226) |
| PIN | best > fair on n=226 and E2 trunk-forward 1.0 |
| not this card | SECOND_SLOT=4, HEAD=3, HARD=6, POS=3, TYPE=3, another LR, Jev ingest, force of the label packet |

Upsample ladder returns are shrinking (3/4/5 = +2 exacts; 6 = +1). 0.95 on this val is 215/226. Upsample 7 will not get there. The 25 INFERRED proposals from 2026-09-19 stay unsettled. Qwen stays stopped unless the operator re-enables `qwen38-27b.service`.
