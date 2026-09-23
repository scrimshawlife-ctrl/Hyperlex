# Spec 007 — next: morph73 IN FLIGHT (INIT_EXPAND_VOCAB warm morph65)

`name_gate=false`. BEST=**morph65** (held). Upsample freeze = **11+**. Do not run SECOND_SLOT=4.

## Done

1. morph69–72 REJECT. Residual AUTHORIZE=0.
2. morph72: UPSAMPLE **10** non-warm; best **0.9532163742690059** < fair **0.9649122807017544** n=171 → REJECT.

## Next

**morph73 IN FLIGHT** — one-knob `HYPERLEX_INIT_EXPAND_VOCAB=1` warm morph65 on morph72 force/hard (UPSAMPLE=10 held). See `receipts/20260923-morph73-expand-warm-inflight.md`.

Qwen stays stopped unless the operator re-enables `qwen38-27b.service`.
