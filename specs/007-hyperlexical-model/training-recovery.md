# Training recovery: Spec 007 morph log

> WF-003 / prep contract body: unchanged from Hyperlex `main` @ `ede3d6c` (pre-existing mid-sentence truncate). This tip restores that body from main and appends morph47/48 settlement.

## BOUNDARY

This does not govern or activate. Existing doctrine, ontology, name gate and
operator authority remain unchanged. No Notion writeback, training or promotion.

### 2026-09-17 — morph47 curriculum POS=3 → REJECT_VS_BEST

- Lever: `HYPERLEX_UNBIND_CURRICULUM_POS_EPOCHS=3` (was 1); TYPE=1 / HARD=4 / HEAD_SLOT=2 held; morph40 gold; warm morph40 + SAVE_BEST; mem 0.3; 40ep.
- Result: best `unbind_exact=0.7149122807017544` (ep8) < fair morph40 **0.7368421052631579** (n=228) → **REJECT_VS_BEST**.
- Container: `hlx-train-morph47-1789633911` exit 0. E2 PASS. BEST remains morph40.
- Workspace: `receipts/20260917-morph47-40ep-reject-vs-best.md`, `receipts/morph47-40ep-curriculum-pos3-20260917/`.

### 2026-09-17 — morph48 LAST_TRAINABLE=6 → PROMOTE_BEST

- Lever: `HYPERLEX_LAST_TRAINABLE=6` (was 4); POS=1 / HARD=4 / HEAD_SLOT=2 held; morph40 gold; warm morph40 + SAVE_BEST; mem 0.3; 40ep.
- Result: best `unbind_exact=0.7412280701754386` (ep19) > fair morph40 **0.7368421052631579** (n=228); E2 PASS → **PROMOTE_BEST**.
- Spark BEST symlink → `seed-morph48`. morph40 + morph36 preserved. `name_gate=false`.
- Container: `hlx-train-morph48-1789639062` exit 0 (launched by `bc-3e55c42d`).
- Workspace: `receipts/20260917-morph48-40ep-promote-best.md`, `receipts/morph48-40ep-last6-20260917/`.
