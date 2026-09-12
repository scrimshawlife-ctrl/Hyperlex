# 007 Hyperlexical — pickup after morph14 (2026-09-12)

## Current State
- **BEST (observed):** `seed-morph14` · civilian val `unbind_exact≈0.3857` · slot/token F1≈0.659 · classify≈0.438 · E2 PASS
- Ladder on exact: **0.45 / 0.55 / 0.65** (gap to first rung ≈0.064)
- Latest harness on `main`: `HYPERLEX_UNBIND_PRIMARY=slot_ce` (default off) + token/slot F1 + morph/curriculum/INFERRED-weight/hard-atoms recipe
- `name_gate=false`. Do not Hub. Do not invent OBSERVED gold.
- Notion Operator Hub was stale on morph3 (0.358) — sync to morph14.

## Prioritized Plan (execute in order)
1. **Sync operator pins** to morph14 (Notion Hub, BEST-CHECKPOINT, STATUS notes).
2. **Run morph15 Spark card** (see `u3-recipe.md` / `AARON-SPARK-TRAIN.md`):
   - `slot_ce` + OBSERVED upsample 2 + INFERRED_WEIGHT 0.5
   - curriculum 2+1+remainder · hard_upsample 3 · residual dump on
   - OUT `…-seed-morph15`
3. **Read residual themes** (`HYPERLEX_UNBIND_RESIDUAL_DUMP`) — head-slot vs morph_bleed vs order.
4. **Hold** MORPH_CLUSTERS churn and hard INFERRED_CAP (Morph4/5 lessons).
5. If exact ≥0.45: pin new BEST, keep `name_gate` false until Danny says otherwise.
6. Spec 008 draft (#31) stays hold — not this lane.

## Success Criteria
- morph15 receipt + residual summary returned to Danny
- `unbind_exact` moves toward 0.45 without classify collapse
- `name_gate` still false
- No weights / hard-atoms JSONL in git

## Risks/Notes
- This cloud box has no Spark / no local SoT — train stays on DGX Spark.
- F1≈0.659 with exact≈0.386 means near-misses dominate; residual dump is the next signal, not another flat loss weight.
