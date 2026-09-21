# Spec 007 — next card: OBSERVED upsample 10; BEST=morph63

`name_gate=false`. morph64 observed upsample 9 **tied** fair morph63 (193/226). Do not replay upsample 9. Do not run second-slot weight 4. Do not add gold.

## One knob

`HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=10` (9 rejected as tie; not stacked with another lever). Residuals on BEST morph63 are 33, of which 25 are OBSERVED (`partial_slot_miss` 20).

Hold from morph63: warm morph63, `SECOND_SLOT=2`, LR=2e-5, LAST=8, HEAD=2, POS=1, TYPE=1, HARD=4, force 137, mem 0.3 exclusive, 40ep, SAVE_BEST.

| | |
|--|--|
| fair | **0.8539823008849557** n=226 (193/226) |
| PIN | best > fair on n=226 and E2 trunk-forward 1.0 |
| not this card | SECOND_SLOT=4, HEAD=3, HARD=6, POS=3, TYPE=3, another LR, Jev ingest, force of the label packet |

Upsample ladder: 3/4/5 = +2; 6/7/8 = +1; **9 = +0 tie**. 0.95 on this val is 215/226. Upsample 10 will not get there. The 25 INFERRED proposals from 2026-09-19 stay unsettled. Qwen stays stopped unless the operator re-enables `qwen38-27b.service`.
