# morph60 IN FLIGHT — observed upsample 5 (2026-09-19)

Container `hlx-train-morph60-1789829154`. One knob `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=5`. Held `HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=2`, warm morph59, LAST=8, HEAD=2, POS=1, TYPE=1, HARD=4, force 137, mem 0.3, 40ep, SAVE_BEST. Fair **0.831858407079646** n=226. `name_gate=false`. No new gold. The 2026-09-19 label packet is not integrated.

Spark poll `poll_morph60.sh` runs E2 then `finish_morph60.py` when the container exits and `train-receipt.json` exists. PIN only if best is strictly greater than fair on n=226 and E2 trunk-forward exact is 1.0.
