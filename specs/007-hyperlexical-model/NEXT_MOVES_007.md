# Spec 007 — next card: OBSERVED upsample 8; BEST=morph62

`name_gate=false`. morph62 observed upsample 7 beat fair morph61 by one exact. Do not replay upsample 7. Do not run second-slot weight 4. Do not add gold.

## One knob

`HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=8` (7 just promoted; not stacked with another lever). Residuals on the pin are 34, of which 26 are OBSERVED (`partial_slot_miss` 21).

Hold from morph62: warm morph62, `SECOND_SLOT=2`, LR=2e-5, LAST=8, HEAD=2, POS=1, TYPE=1, HARD=4, force 137, mem 0.3 exclusive, 40ep, SAVE_BEST.

| | |
|--|--|
| fair | **0.8495575221238938** n=226 (192/226) |
| PIN | best > fair on n=226 and E2 trunk-forward 1.0 |
| not this card | SECOND_SLOT=4, HEAD=3, HARD=6, POS=3, TYPE=3, another LR, Jev ingest, force of the label packet |

Upsample ladder returns are shrinking (3/4/5 = +2 exacts; 6/7 = +1). 0.95 on this val is 215/226. Upsample 8 will not get there. The 25 INFERRED proposals from 2026-09-19 stay unsettled. Qwen stays stopped unless the operator re-enables `qwen38-27b.service`.
