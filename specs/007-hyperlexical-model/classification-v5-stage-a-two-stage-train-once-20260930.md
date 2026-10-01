# Classification v5 — Train two-stage Stage-A once

```text
RULE = TRAIN_V5_STAGE_A_TWO_STAGE_ONCE / HYPERLEX_V5_STAGE_A_TWO_STAGE_TRAIN_V1
EXPERIMENT_ID = HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-001
DATASET = V1R9 / 8d4be830… (unchanged)
ARCHITECTURE_RECEIPT = 631427cc…
CLASS_WEIGHT_ARTIFACT = 5496015a…
TRAINING_CONFIG = 0117faca…
AUTH_RECEIPT = c9b262de…
SPLIT_WITNESS = ecb88025…
SELECTED = cd2829c1…
SCIENTIFIC_RESULT = SETTLED_PASS
BEST = 9fba0f66… UNCHANGED
RESERVE = unused
promotion_candidate = true
```

Exactly one authorized run. Literal class weights consumed (not recomputed).
Frozen V1R9 train/validation membership (`HYPERLEX_V5_STAGE_A_TWO_STAGE_DATASET_SPLIT_V1`).

## Preflight

Authorization gates PASS. Split witness verified before first optimizer step:
`train_rows=4437`, Gate1 3554+883, Gate2 eligible 883, identity overlaps 0,
`drop_last=false`, full-pass shuffle seed 42, steps/epoch 555.

## Train

| Field | Value |
|---|---|
| Epochs ran | 12 |
| Selected epoch | 11 |
| Optimizer steps | 6660 (555×12) |
| Selection score | 0.8167525809111703 |
| Gate1 macro-F1 (sel) | 0.8532186691158052 |
| Gate2 macro-F1 (sel) | 0.7802864927065354 |

## Threshold grid

| Field | Value |
|---|---|
| Combinations | 100 |
| Passing | **4** |
| Selected Gate1 | **0.75** |
| Selected Gate2 | **0.50** |

## Acceptance

| Gate | Value | Pass |
|---|---:|---|
| false_entry ≤ 0.05 | 0.04233226837060703 | PASS |
| PRESENT recall ≥ 0.70 | 0.7048665620094191 | PASS |
| NONE recall ≥ 0.90 | 0.9089456869009584 | PASS |
| End-to-end macro-F1 | 0.7411485290305739 | — |
| UNCERTAIN recall | 0.6790123456790124 | — |

## Routing (validation)

| | |
|---|---:|
| PRESENT FN blocked Gate1 | 126 |
| PRESENT FN rejected Gate2 | 62 |
| NONE leaked Gate1 | 114 |
| NONE leaked both → PRESENT | 53 |
| UNCERTAIN blocked Gate1 | 27 |
| UNCERTAIN correctly routed | 110 |
| UNCERTAIN promoted PRESENT | 25 |

## Next action

```text
NEXT_ACTION = STOP_OR_PROMOTE_REVIEW
```

Do not auto-move BEST. Promotion remains a human decision.

Promotion review (read-only): see
`classification-v5-stage-a-two-stage-promotion-review-20260930.md`
→ **`PROMOTION_READY`** / `PROMOTE_V5_STAGE_A_TWO_STAGE_SELECTED`.

Receipt: `classification-v5-stage-a-two-stage-train-once-receipt-20260930.json`
(`9c358d2c…`).
