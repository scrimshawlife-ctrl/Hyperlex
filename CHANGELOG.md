# Changelog

## Unreleased

- **Spec 007 morph50 PROMOTE BEST:** `LAST_TRAINABLE=8` (MAX) warm morph49 +
  SAVE_BEST + +2 METHOD morph49 residual gold (force 137 / hard 182;
  SoT flip `boon coon`) → best **0.8097** (ep38) > fair morph49
  **0.7920** (n=226). E2 PASS. Spark BEST → morph50;
  morph49+morph48+morph40+morph36 preserved. Container
  `hlx-train-morph50-1789703143` exit 0. Receipts:
  `receipts/20260918-morph50-40ep-promote-best.md`,
  `receipts/morph50-40ep-last8-20260918/`.

- **Spec 007 head-slot CE upweight + morph15 recipe preflight:**
  `HYPERLEX_UNBIND_HEAD_SLOT_WEIGHT` (default 1.0, fail-closed in
  (0, 4]) scales position-0 filler CE before `combine_unbind_train_terms`.
  Targets `positional_head_filler_miss` without inventing gold. Receipt /
  `config-train.json` carry `unbind_head_slot_weight`. Torch-free
  `python3 -m hyperlexical.morph15_recipe` resolves the morph15 card
  knobs (exit 2 bad env, exit 3 hard-atoms missing when upsample>1).
  Spark `morph15-unbind.sh` defaults head weight **2** and runs recipe
  preflight. `name_gate` stays false.
