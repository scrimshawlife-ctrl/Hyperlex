# morph64 IN FLIGHT — observed upsample 9 (2026-09-20)

Container `hlx-train-morph64-1789928581`. One knob `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=9`. Held `HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=2`, warm morph63, LAST=8, HEAD=2, POS=1, TYPE=1, HARD=4, force 137, mem 0.3 exclusive, 40ep, SAVE_BEST. Fair **0.8539823008849557** n=226. `name_gate=false`. No new gold. Label packet not integrated. Qwen remains stopped+disabled.

Spark poll `poll_morph64.sh` runs E2 then `finish_morph64.py` when the container exits and `train-receipt.json` exists. PIN only if best is strictly greater than fair on n=226 and E2 trunk-forward exact is 1.0.
