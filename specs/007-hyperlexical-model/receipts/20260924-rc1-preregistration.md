# rc1 pre-registration — clean release candidate (2026-09-24)

**Operator:** Danny `okay continue as recommended` (clean cold-start retrain + one test-split score, D7). Committed **before** training.

## Candidate

`seed-rc1` = morph78 recipe with three changes (`scripts/spark/soft_ceiling/rc1-train-env.json`):

1. **Cold start** from `answerdotai/ModernBERT-base` (no `HYPERLEX_INIT_FROM`; morph65/78 weights saw the Wiktionary rows).
2. `HYPERLEX_FILLER_FILTER=strict` (D8).
3. `HYPERLEX_RELEASE_SET=1` (D5b): drops CC BY-SA rows and same-text rows. Export 9,150 → 7,805 rows; classify train 3,568; unbind train 11,454; filler vocab 1,480.

Same otherwise: 40 epochs, lr 2e-5, batch 8, LAST_TRAINABLE 8, observed upsample 10, legacy task routing, morph78 force/hard files. Code: `main` @ `ed27545`.

## Frozen evaluation (`rc1-prereg-20260924/holdout-manifest-rc1.json`)

Status `FROZEN_NOT_SCORED`. Release surface, test split only, exclusions for every row in morph78/morph50 force/hard files (the files rc1 also trains on) or train text.

| Slice | n |
|---|--:|
| unbind clean | 306 |
| unbind OOV-filler | 10 |
| classify clean | 444 (OBSERVED 72, INFERRED 372) |

Models scored once, together: `seed-rc1`, `seed-morph78`, `seed-morph65`. Baselines: `unbind_copy_token`, `classify_majority_train`. Calibration: each model's temperature + abstain threshold fitted on its **clean val** (`calibrate_classify.py`) before test is scored.

## Decision rule (stated in advance)

rc1 is the **release candidate** if all hold:

1. Trained trunk-forward E2 PASS.
2. Corrected soft_ceiling gate on clean val does not show rc1 below morph78 (decision recorded either way; a tie is acceptable because rc1's point is clean data).
3. Test (non-inferiority vs morph78): unbind clean exact ≥ morph78 − 0.01; classify accuracy (all) ≥ morph78 − 0.02; classify accuracy (OBSERVED labels) ≥ morph78 − 0.05 (n=72, noisy).
4. Test classify accuracy > `classify_majority_train`.
5. Shipped `filler_vocab` passes `assert_publishable_vocab`.

Reported regardless, not gating: unbind vs `unbind_copy_token` (unbind on whitespace atoms may be matched by copying), OOV-filler slice (n=10), ECE, abstain rate.

If rc1 fails, BEST stays morph78, rc1 is not promoted, and the finding is recorded. `name_gate` (A6) stays on `seed-morph78` unless an operator sentence moves it. No Hub upload in any case (D4 pending).
