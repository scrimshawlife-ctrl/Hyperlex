# morph43 REJECT_VS_BEST

**Authority:** Spec 007. Held residual gold promote. `name_gate=false`.
**BEST:** morph40 held (unchanged). morph36 preserved.

## Gate

| metric | value |
|--------|------:|
| morph43 best unbind_exact (ep2) | **0.9379** |
| morph40 fair baseline (n=177) | **0.9492** |
| beats fair? | **False** |
| morph43 final ep39 | 0.8870 |
| E2 | PASS (1.0) |
| mem_fraction | **0.3** |
| wall | **~86.3 min** |

## Lever

Held residual gold: authorize **51** / abstain **9**; force-train **135→186**; hard_atoms **180→226**; warm morph40 + SAVE_BEST_UNBIND 40ep @ mem 0.3.

## Verdict

**REJECT_VS_BEST** — best 0.9379 < fair morph40 0.9492 on the same val n=177.
Do not promote. BEST stays morph40.
