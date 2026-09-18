# morph50 PROMOTE BEST (2026-09-18)

**Authority:** Spec 007. `name_gate=false`.

## Result

| field | value |
|-------|------:|
| best unbind_exact | **0.8097345132743363** (ep38) |
| fair morph49 | **0.7920353982300885** (n=226) |
| E2 trunk-forward | **PASS** (1.0) |
| decision | **PROMOTE_BEST** |

## Lever

`HYPERLEX_LAST_TRAINABLE=8` (MAX; was 7) +2 METHOD morph49 residual gold  
(`TOKEN:jailbreak SLOT:prompt`; `boon coon` SoT flip). Warm morph49 + `SAVE_BEST_UNBIND=1`; mem 0.3; 40ep.

Container: `hlx-train-morph50-1789703143` (Exited 0).  
Spark BEST → `seed-morph50`. Preserved: morph49, morph48, morph40, morph36.

## Coordination

Sibling gate owner `bc-b4ecc915-ddac-5aaa-9cce-e29d15c18061` was RUNNING/silent; coordinator claimed `morph50-gate.lock`, polled to end, gated, promoted.

Receipts: `receipts/morph50-40ep-last8-20260918/`.
