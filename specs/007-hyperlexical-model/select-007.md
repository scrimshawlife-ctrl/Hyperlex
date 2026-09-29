# SELECT-007

Experiment `HLX-EXP-2026-09-29-SELECT-007`.

The only scientific intervention is the classify sampling policy. Both arms use the current default schedule: max 12 epochs, minimum 4, patience 4, strict improvement, ties keep the earlier checkpoint, restore best. BEST is not moved. PASS does not promote.

`HLX_SEED` unset does not define epoch sampling. The frozen rule is `inferred_none_circular_sha256_v1`:

- Identity is `normalized_text_sha256` of the row text.
- Keep every non-none classify training row.
- Keep all 219 OBSERVED none rows.
- Sort INFERRED none rows by identity, then original index.
- For one-based epoch `e`, start at `((e - 1) * 219) mod 1935` and take 219 rows circularly.
- Kept rows stay in their original training order.
- Selection does not use predictions, loss, difficulty, or reserve performance.
- The control arm keeps all 1935 INFERRED none rows.

The SELECT-006 reserve stays bound to SELECT-006. This experiment builds a fresh reserve with the existing Wiktionary sense-label recipe.

## Settlement

Preregistration sha256 `3b729181ea17b0a10405612605fe0e6a539f11a79605d34ad9d53ef94b7807c0`.

Lifecycle `SETTLED_FAIL`. promotion_eligible false. promotion_applied false. BEST `9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6` before and `9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6` after.

Control epochs 6, steps 20118, macro-F1 0.40952380952380957.
Candidate epochs 9, steps 28251, macro-F1 0.42164502164502166.
Delta 0.012121212121212088.

Gates: `{"classification_accuracy": "PASS", "classify_macro_f1_nonnone": "PASS", "observed_label_accuracy": "PASS", "predicted_none_rate": "FAIL", "unbind_clean_exact": "PASS"}`.

Control classification accuracy 0.34375, observed accuracy 0.34375, unbind exact 0.2727272727272727, predicted none rate 0.3125.
Candidate classification accuracy 0.34375, observed accuracy 0.34375, unbind exact 0.2727272727272727, predicted none rate 0.3125.

Control kept 1935 INFERRED none rows each epoch. The candidate kept 219. The fresh reserve is 32 OBSERVED head-mapped classify rows and 11 unbind_clean rows. The none-rate gate failed because the rates were equal.
