# RECEIPT — accept20 prepare; famcls34 REJECT; famcls35 climb (2026-09-14)

**Authority:** Spec 007. SHADOW / `name_gate=false`. BEST untouched.

## Pins
- Weights: famcls25
- Data: **accept20** (`p1-classify-accept20-20260914/prepare`)
- BEST: morph19

## famcls34 — REJECT
- AUX=0.05, UPSAMPLE=1, LR 1e-5 on accept19
- Holdout: family **0.9080**, structure/pointer **0.875**

## accept20
- +149 novel residual contrastive rows from famcls25 accept19-test dump (11 misses)
- Fair famcls25 baseline: family **0.9285714285714286**, structure/role/pointer **1.0**

## famcls35 — IN FLIGHT
- N=8, LR 1e-5, no aux, init famcls25, data accept20, 40 ep
- Path: `~/hlx-private/p1-structure-unbind-famcls35-20260914/`
