# Spec 007 — next after morph67 REJECT + morph68 residual-gold launch

`name_gate=false`. BEST=**morph65** (held). Upsample ladder frozen. Do not run SECOND_SLOT=4.

## Done

1. morph67 SoT-flip **REJECT_VS_BEST**: best **0.9597989949748744** (ep18, 191/199) < fair **0.9698492462311558** (193/199). E2 PASS. BEST stays morph65.
2. METHOD morph43 on morph67 residuals n=8 → AUTHORIZE **2** / ABSTAIN **6**.
3. Force/hard expand: **force_added=2** / **hard_added=2** → 166 / 208. Harvest OBSERVED append for both AUTHORIZE. Force moves **166/166**; fair morph65 **0.9695431472081218** (191/197).
4. **In flight:** morph68 warm morph65, UPSAMPLE=8, SECOND_SLOT=2, force/hard morph68 expanded, exclusive 0.3.

## Gate (when morph68 exits)

PIN iff best > fair **0.9695431472081218** (n=197) and E2 trunk-forward `unbind_exact=1.0`. Else REJECT; BEST stays morph65.

AUTHORIZE texts: `[Out:] Mega yachts [In:] Mega gyatt`, `an egg's age`.

Qwen stays stopped unless the operator re-enables `qwen38-27b.service`.
