# Spec 007 — next after morph68 tie + morph69 unused METHOD gold

`name_gate=false`. BEST=**morph65** (held). Upsample ladder frozen. Do not run SECOND_SLOT=4.

## Done

1. morph68 hang-fix relaunch `hlx-train-morph68-1790047095` past ep4; best **0.9695431472081218** @ ep27 **=** fair **0.9695431472081218** n=197 → **REJECT_VS_BEST** (strictly greater required).
2. morph68 best residuals n=6 → METHOD AUTHORIZE **0** / ABSTAIN **6** (scaffolding). Do not burn force_added=0.
3. **Goldens updated:** unused METHOD AUTHORIZE morph43/morph50 residual gold → **force_added=26** / hard_added=25 (192/233). Fair morph65 **0.9649122807017544** n=171.

## Next / in flight

morph69 warm morph65, UPSAMPLE=8, SECOND_SLOT=2, force/hard morph69, exclusive 0.3, hang-fix `loop.py`.
PIN iff best > fair **0.9649122807017544** (n=171) and E2 trunk-forward `unbind_exact=1.0`.

Qwen stays stopped unless the operator re-enables `qwen38-27b.service`.
