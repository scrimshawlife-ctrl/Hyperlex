# morph58 IN FLIGHT — observed upsample 3 (2026-09-19)

Container `hlx-train-morph58-1789793254`. One knob `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=3`. Held `HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=2`, warm morph56, LAST=8, HEAD=2, POS=1, TYPE=1, HARD=4, force 137, mem 0.3, 40ep, SAVE_BEST. Fair **0.8185840707964602** n=226. `name_gate=false`. No new gold. The 2026-09-19 label packet is not integrated.

Spark poll `poll_morph58.sh` runs E2 then `finish_morph58.py` when the container exits and `train-receipt.json` exists. PIN only if best is strictly greater than fair on n=226 and E2 trunk-forward exact is 1.0.
