# Classification v5 — Train two-stage Stage-A once on V1R1

```text
RULE = TRAIN_V5_STAGE_A_TWO_STAGE_GENERALIZATION_ONCE
EXPERIMENT_ID = HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-GENERALIZATION-001
DATASET = V1R1 / 4095036e…
AUTH = f7d4f3ad…
CONFIG = 1527ae18…
WEIGHTS = 80b7f899…
INIT = FRESH_RETRAIN_FROM_MODEL_WIDE_BEST / 9fba0f66…
STAGE_A_BEST = cd2829c1… UNCHANGED (not loaded)
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
SCIENTIFIC_RESULT = SETTLED_FAIL
TRAINING_STATUS = COMPLETE
n_threshold_passing = 0
TRAINING_RUN_LIMIT = 1 (exhausted)
SPENT_RESERVE = SPENT / unused / overlap 0
```

Single authorized fresh retrain. Class weights consumed as sealed literals.
No V1R1 mutation. No architecture change. No Stage-B mutation. No BEST moves.
Spent reserve not loaded for train/val/threshold/checkpoint/diagnostics.

## Execution

| Field | Value |
|---|---|
| Preflight | PASS (all auth/split/weight/config/init pins) |
| Execution validity | VALID |
| Epochs completed | 12 |
| TRAIN_DATALOADER_LEN | 317 |
| Optimizer steps | 3804 (= 12 × 317) |
| Selected epoch | 12 |
| Selection score | 0.8976427205356838 |
| Selected checkpoint | `26841d5f…` |
| Gate1 macro-F1 @ sel | 0.8396571450175399 |
| Gate2 macro-F1 @ sel | 0.9556282960538279 |

## Threshold search / acceptance

100-pair grid evaluated. **0 pairs** satisfied all three mandatory gates →
`SETTLED_FAIL`. No threshold selected. Fail-display operating point for
diagnostics only: Gate1=0.50 / Gate2=0.50.

| Gate | Value @ 0.50/0.50 | Required | Pass |
|---|---:|---:|---|
| false_entry on NONE | 0.2014 | ≤ 0.05 | FAIL |
| EVIDENCE_PRESENT recall | 0.8907 | ≥ 0.70 | PASS |
| NO_EVIDENCE recall | 0.7845 | ≥ 0.90 | FAIL |

## Critical cell diagnostics (@ fail-display 0.50/0.50)

| Cell | n | recall | false-entry | G1 block | G2 reject |
|---|---:|---:|---:|---:|---:|
| SHORT_ATOM/NONE | 152 | 0.454 | **0.546** | 0.454 | 0.000 |
| SHORT_ATOM/PRESENT | 156 | 0.750 | — | 0.250 | 0.000 |
| DEFINITION_STYLE/NONE | 139 | 0.885 | 0.094 | 0.885 | 0.188 |
| DEFINITION_STYLE/PRESENT | 80 | 0.963 | — | 0.025 | 0.013 |
| PROSE/NONE | 95 | 0.832 | 0.168 | 0.832 | 0.000 |
| PROSE/PRESENT | 79 | 0.949 | — | 0.051 | 0.000 |
| ORDINARY_PROSE/NONE | 180 | 0.961 | 0.011 | 0.961 | 0.714 |
| ORDINARY_PROSE/PRESENT | 106 | 1.000 | — | 0.000 | 0.000 |

SHORT_ATOM NONE false-entry and SHORT_ATOM PRESENT recall did **not** improve
together into an accepting regime: PRESENT surface recall is usable (0.75) while
NONE false-entry remains ~0.55 on the short-atom cell (and drives aggregate
false-entry / NONE-recall failure).

## vs current STAGE_A_BEST (read-only deltas @ 0.50/0.50 display)

| Metric | STAGE_A_BEST ref | This run | Δ |
|---|---:|---:|---:|
| false_entry | 0.0423 | 0.2014 | +0.1591 |
| PRESENT recall | 0.7049 | 0.8907 | +0.1858 |
| NONE recall | 0.9089 | 0.7845 | −0.1244 |
| UNCERTAIN recall | 0.6790 | 0.8657 | +0.1867 |
| e2e macro-F1 | 0.7411 | 0.8412 | +0.1001 |

Higher PRESENT/UNCERTAIN/macro-F1 at the display point; false-entry and NONE
recall worse. Not a promotion candidate.

## Promotion / BEST

```text
promotion_candidate = false
STAGE_A_BEST = cd2829c1… UNCHANGED
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
```

## Artifacts

Private run root:
`/home/morpheus/hlx-private/classification-v5-stage-a-two-stage-generalization-train-v1-20261001/classification-v5-stage-a-two-stage-generalization-001`

```text
RUN_RECEIPT_SHA256 = 35d9a706…
SELECTED_CHECKPOINT_SHA256 = 26841d5f…
TWO_STAGE_SPLIT_WITNESS_SHA256 = 44f5841f…
```

Receipt: `classification-v5-stage-a-two-stage-generalization-train-once-receipt-20261001.json`

## Next action

```text
NEXT_ACTION = DIAGNOSE_V5_STAGE_A_GENERALIZATION_RETRAIN_SETTLED_FAIL
```

Do not retrain (run limit exhausted). Do not promote. Do not touch spent reserve.
