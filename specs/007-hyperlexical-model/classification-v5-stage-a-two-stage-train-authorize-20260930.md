# Classification v5 — Authorize two-stage Stage-A train

```text
RULE = AUTHORIZE_V5_STAGE_A_TWO_STAGE_TRAIN_V1 / HYPERLEX_V5_STAGE_A_TWO_STAGE_TRAIN_V1
EXPERIMENT_ID = HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-001
ARCHITECTURE_RECEIPT = 631427cc…
DATASET = V1R9 / 8d4be830…
BEST = 9fba0f66… UNCHANGED
TRAIN = false
TRAIN_AUTHORIZED = true
TRAINING_STATUS = AUTHORIZED_NOT_STARTED
SCIENTIFIC_RESULT = NOT_COMPUTABLE
RESERVE = unused
```

Authorization only. Class weights resolved **before** `TRAIN_AUTHORIZED=true`.
No train. V1R9 body unchanged. Graph unchanged.

## Pre-authorization: `RESOLVE_V5_TWO_STAGE_CLASS_WEIGHTS`

Train split only (`n=4437`; `train_split_sha256=cee13cbe…`).

### Gate 1

| Class | rows | OBSERVED | INFERRED | effective | final weight |
|---|---:|---:|---:|---:|---:|
| NO_EVIDENCE | 3554 | 319 | 3235 | 1936.5 | **0.7182189774877286** |
| POSSIBLE_EVIDENCE | 883 | 333 | 550 | 608.0 | **1.2817810225122714** |

### Gate 2 (PRESENT+UNCERTAIN only; NONE excluded)

| Class | rows | OBSERVED | INFERRED | effective | final weight |
|---|---:|---:|---:|---:|---:|
| UNCERTAIN | 280 | 193 | 87 | 236.5 | **1.1124229052629504** |
| CONFIRMED_PRESENT | 603 | 140 | 463 | 371.5 | **0.8875770947370494** |

```text
CLASS_WEIGHT_ARTIFACT_SHA256 = 5496015a…
```

Literal weights are embedded in the resolved training config; the train runner
must verify the weight-artifact SHA and **must not recompute**.

## Pins

| Field | Value |
|---|---|
| Architecture receipt | `631427cc…` |
| Dataset | `8d4be830…` |
| BEST | `9fba0f66…` |
| TRAINING_CONFIG_SHA256 | `0117faca…` |
| AUTHORIZATION_RECEIPT_SHA256 | `c9b262de…` |
| TRAINING_RUN_LIMIT | 1 |

## Architecture / loss (frozen)

- Shared ModernBERT; CLS pool; Gate1/Gate2 linear 2-logit heads
- Trainable: last 2 encoder layers + both heads
- `L_total = L_gate1 + 1.0 * L_gate2`; binary weighted CE; no focal
- Opt: AdamW lr=2e-5 wd=0.01 batch=8 accum=1 epochs=12 min=4 patience=4 warmup=0.05 clip=1.0 seed=42 max_len=64

## Acceptance / thresholds

Unchanged end-to-end gates; 10×10 Gate1/Gate2 threshold grid; checkpoint
`0.5*G1_macroF1 + 0.5*G2_macroF1`.

## Runner

`scripts/spark/run_classification_v5_stage_a_two_stage_train.py` fails closed
unless authorization gates pass and `HLX_V5_STAGE_A_EXECUTE_TRAIN=1`.

Private auth dir:
`/home/morpheus/hlx-private/classification-v5-stage-a-two-stage-train-v1-20260930`

## Next action

```text
NEXT_ACTION = TRAIN_V5_STAGE_A_TWO_STAGE_ONCE
```

Stop. Do not train in this execution.

Receipt: `classification-v5-stage-a-two-stage-train-authorize-receipt-20260930.json`
(`c9b262de…`).
