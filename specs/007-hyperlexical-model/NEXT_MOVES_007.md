# Spec 007 — next after morph66: watch gold gate; freeze upsample

`name_gate=false`. BEST=**morph65** (`0.8584070796460177`, 194/226). Upsample ladder frozen (3..10 done; no 11+). Do not run second-slot weight 4.

## In flight

**morph66** `hlx-train-morph66-1789969749` — one knob force/hard residual gold 164/206. Warm morph65. Hold UPSAMPLE=8, SECOND_SLOT=2, LAST=8, HEAD=2, POS=1, TYPE=1, HARD=4, mem 0.3 exclusive, 40ep, SAVE_BEST.

| | |
|--|--|
| fair | **0.9601990049751243** n=201 (193/201) — morph65 on post-force val |
| PIN | best > fair on n=201 and E2 trunk-forward 1.0 |
| not this card | upsample 11+, SECOND_SLOT=4, invent gold, Hub |

## Done

1. Packet settle 25 AUTHORIZE → OBSERVED.
2. morph63 residual gold AUTHORIZE 27 / ABSTAIN 6 → force 164 / hard 206.
3. morph65 PROMOTE (+1 exact vs morph63).
4. Fair-eval morph65 on new force surface → 0.9602 @ n=201.

Qwen stays stopped unless the operator re-enables `qwen38-27b.service`.
