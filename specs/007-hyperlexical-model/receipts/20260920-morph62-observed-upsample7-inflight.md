# morph62 IN FLIGHT — observed upsample 7 (2026-09-20)

Container `hlx-train-morph62-1789896471`. One knob `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=7`. Held `HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=2`, warm morph61, LAST=8, HEAD=2, POS=1, TYPE=1, HARD=4, force 137, mem 0.3 exclusive, 40ep, SAVE_BEST. Fair **0.8451327433628318** n=226. `name_gate=false`. No new gold. The 2026-09-19 label packet is not integrated. Qwen remains stopped+disabled.

Spark poll `poll_morph62.sh` runs E2 then `finish_morph62.py` when the container exits and `train-receipt.json` exists. PIN only if best is strictly greater than fair on n=226 and E2 trunk-forward exact is 1.0.
