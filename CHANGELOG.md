# Changelog

## Unreleased

- **Spec 007 morph61 PROMOTE_BEST:** `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=6`
  warm morph60, second-slot weight 2 held. Best **0.8451327433628318**
  (ep26, 191/226) > fair morph60 **0.8407079646017699** (n=226). E2
  trunk-forward PASS (`unbind_exact=1.0`). Spark BEST → morph61. morph60
  weights kept. Container `hlx-train-morph61-1789880707` exit 0 after
  exclusive remount (Qwen stopped+disabled). `name_gate=false`. No new gold.
  Receipt: `receipts/20260920-morph61-40ep-promote-best.md`.

- **Spec 007 morph60 PROMOTE_BEST:** `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=5`
  warm morph59, second-slot weight 2 held. Best **0.8407079646017699**
  (ep9, 190/226) > fair morph59 **0.831858407079646** (n=226). E2
  trunk-forward PASS (`unbind_exact=1.0`). Spark BEST → morph60. morph59
  weights kept. Container `hlx-train-morph60-1789829154` exit 0.
  `name_gate=false`. No new gold.
  Receipt: `receipts/20260919-morph60-40ep-promote-best.md`.

- **Spec 007 morph59 PROMOTE_BEST:** `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=4`
  warm morph58, second-slot weight 2 held. Best **0.831858407079646**
  (ep14, 188/226) > fair morph58 **0.8230088495575221** (n=226). E2
  trunk-forward PASS (`unbind_exact=1.0`). Spark BEST → morph59. morph58
  weights kept. Container `hlx-train-morph59-1789803430` exit 0.
  `name_gate=false`. No new gold.
  Receipt: `receipts/20260919-morph59-40ep-promote-best.md`.

- **Spec 007 morph58 PROMOTE_BEST:** `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=3`
  warm morph56, second-slot weight 2 held. Best **0.8230088495575221**
  (ep37, 186/226) > fair morph56 **0.8185840707964602** (n=226). E2
  trunk-forward PASS (`unbind_exact=1.0`). Spark BEST → morph58. morph56
  weights kept. Container `hlx-train-morph58-1789793254` exit 0.
  `name_gate=false`. No new gold.
  Receipt: `receipts/20260919-morph58-40ep-promote-best.md`.

- **Spec 007 morph57 REJECT_VS_BEST:** `HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=3`
  warm morph56. Best **0.8185840707964602** (ep34, 185/226) ties fair
  morph56 on n=226. E2 PASS. Tie is not a promote. BEST stays morph56.
  Container `hlx-train-morph57-1789775196` exit 0. `name_gate=false`.
  Receipt: `receipts/20260919-morph57-40ep-reject-tie.md`.

- **Spec 007 morph56 PROMOTE_BEST:** `HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=2`
  on the morph50 surface. Best **0.8185840707964602** (ep10, 185/226) >
  fair morph50 **0.8097345132743363** (n=226). E2 trunk-forward PASS
  (`unbind_exact=1.0`). Spark BEST → morph56. morph50 weights kept.
  Container `hlx-train-morph56-1789766977` exit 0. `name_gate=false`.
  Receipt: `receipts/20260918-morph56-40ep-promote-best.md`.

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

<!-- Full Unreleased history: restore from Hyperlex main @ e32c1f5 + morph50 prepend when convenient. -->
