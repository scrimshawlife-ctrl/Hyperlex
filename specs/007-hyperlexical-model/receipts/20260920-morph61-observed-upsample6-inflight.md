# morph61 IN FLIGHT — observed upsample 6 (2026-09-20)

Container `hlx-train-morph61-1789880707`. One knob `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=6`. Held `HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=2`, warm morph60, LAST=8, HEAD=2, POS=1, TYPE=1, HARD=4, force 137, mem **0.3 exclusive**, 40ep, SAVE_BEST. Fair **0.8407079646017699** n=226. `name_gate=false`. No new gold.

## Spark note

First launch OOM'd beside `qwen38-27b` (~100 GB resident). Operator authorized kill. systemd unit `qwen38-27b.service` was **stopped and disabled** so it would not auto-revive. Remounted exclusive. Guard: `frac=0.3 cap=39.2GB free=113.8GB`.

Spark poll `poll_morph61.sh` runs E2 then `finish_morph61.py` when the container exits and `train-receipt.json` exists. PIN only if best is strictly greater than fair on n=226 and E2 trunk-forward exact is 1.0.
