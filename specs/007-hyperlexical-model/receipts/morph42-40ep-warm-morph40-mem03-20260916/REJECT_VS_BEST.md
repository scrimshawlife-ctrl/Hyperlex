# morph42 REJECT_VS_BEST

**Authority:** Spec 007. No new gold. `name_gate=false`.
**BEST:** morph40 held (unchanged). morph36 preserved.

## Gate

| metric | value |
|--------|------:|
| morph42 best unbind_exact (ep3) | **0.7149** |
| morph40 fair baseline (n=228) | **0.7368** |
| beats fair? | **False** |
| E2 | PASS (1.0) |
| mem_fraction this run | **0.3** |
| wall | **~87.1 min** |

## Lever

`HYPERLEX_CUDA_MEM_FRACTION=0.3` (vs morph41 0.015); warm morph40 BEST + SAVE_BEST_UNBIND 40ep; force-train 135 / hard_atoms 180 unchanged.

## Speed note

morph39/40/41 @ 0.015: ~73 / ~80 / ~85 min. morph42 @ 0.3: **~87 min** — no wall speedup; ModernBERT last-N batch8 still ~1.2 GiB resident; allocator cap was not the bottleneck.

## Verdict

**REJECT_VS_BEST** — best 0.7149 < fair morph40 0.7368 on the same val.
Do not promote. BEST stays morph40.
