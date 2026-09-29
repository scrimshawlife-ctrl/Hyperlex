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
