# morph45 — recipe HEAD_SLOT=3 CLOSED → REJECT (2026-09-16/17)

**Authority:** Spec 007. `name_gate=false`.  
**BEST held:** **morph40** (`unbind_exact≈0.7368` ep9, fair val n=228). morph36 preserved.

## Lever

`HYPERLEX_UNBIND_HEAD_SLOT_WEIGHT=3` (was 2) on morph40 gold surface (force 135 / hard 180 / val n=228). Warm morph40 + SAVE_BEST; mem 0.3 exclusive.

## Outcome

| attempt | container | result |
|---------|-----------|--------|
| 1 | `hlx-train-morph45-1789619192` | exit 137 mid-run (external stop after false BLOCKED) |
| 2 relaunch | `hlx-train-morph45-1789620853` | **REJECT_VS_BEST** best **0.7237** (ep2) < fair **0.7368**; final 0.7105; E2 PASS |

See `receipts/20260917-morph45-reject-vs-best.md`.
