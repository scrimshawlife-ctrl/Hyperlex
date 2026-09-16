# morph41 REJECT_VS_BEST

**Authority:** Spec 007. No new gold. `name_gate=false`.  
**BEST:** morph40 held (unchanged). morph36 preserved.

## Gate

| metric | value |
|--------|------:|
| morph41 best unbind_exact (ep3) | **0.7149** |
| morph40 fair baseline (n=228) | **0.7368** |
| beats fair? | **False** |
| E2 | PASS (1.0) |
| mem_fraction this run | **0.015** (next morph → **0.3**) |

## Lever

Warm morph40 BEST + SAVE_BEST_UNBIND 40ep; force-train 135 / hard_atoms 180 unchanged; residual-review 20 auth held out.

## Verdict

**REJECT_VS_BEST** — best 0.7149 < fair morph40 0.7368 on the same val.
Do not promote. BEST stays morph40.
