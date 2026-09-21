# Spec 007 — next after morph67 SoT-flip launch

`name_gate=false`. BEST=**morph65** (held until morph67 gate). Upsample ladder frozen. Do not run SECOND_SLOT=4.

## Done

1. METHOD morph43 on morph65 force residuals n=8 → AUTHORIZE 2 / ABSTAIN 6.
2. Force expand **no-op** (`force_added=0`) — did not burn identical morph67.
3. SoT flip: 2 AUTHORIZE → OBSERVED in harvest sidecar. Force now 164/164 moved; fair morph65 **0.9698 n=199**.
4. **In flight:** morph67 warm morph65, UPSAMPLE=8, SECOND_SLOT=2, same force/hard as morph66, exclusive 0.3.

## Gate (when morph67 exits)

PIN iff best > fair **0.9698492462311558** (n=199) and E2 trunk-forward `unbind_exact=1.0`. Else REJECT; BEST stays morph65.

Qwen stays stopped unless the operator re-enables `qwen38-27b.service`.
