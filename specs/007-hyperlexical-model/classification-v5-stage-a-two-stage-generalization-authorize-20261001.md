# Classification v5 — Authorize two-stage Stage-A retrain on V1R1

```text
RULE = AUTHORIZE_V5_STAGE_A_TWO_STAGE_RETRAIN_ON_GENERALIZATION_SURFACE
EXPERIMENT_ID = HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-GENERALIZATION-001
ARCHITECTURE = HYPERLEX_V5_STAGE_A_TWO_STAGE_DECISION_GRAPH_V1 / 631427cc…
SURFACE = HYPERLEX_V5_STAGE_A_GENERALIZATION_SURFACE_V1R1
DATASET = 4095036e…
READINESS = c4b5fc07… / READY
SURFACE_RECEIPT = 3dbdd9b2…
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
PARENT_STAGE_A_BEST = cd2829c1… reference only (not loaded)
TRAIN = false
TRAIN_AUTHORIZED = true
TRAINING_STATUS = AUTHORIZED_NOT_STARTED
SCIENTIFIC_RESULT = NOT_COMPUTABLE
SPENT_RESERVE = HYPERLEX_V5_PROMOTION_RESERVE_001 / SPENT / overlap 0
TRAINING_RUN_LIMIT = 1
```

New experiment. Does **not** overwrite
`HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-001`. Authorization only.
Class weights resolved **from V1R1 train only** before `TRAIN_AUTHORIZED=true`.
No train. V1R1 body unchanged. Graph unchanged. Stage-B unchanged. BEST pointers
unchanged. Spent reserve unused for train/val/threshold/checkpoint.

## Initialization policy (frozen)

```text
FRESH_RETRAIN_FROM_MODEL_WIDE_BEST
base encoder/trunk overlay = MODEL_WIDE_BEST 9fba0f66…
last-two adapted layers     = from MODEL_WIDE_BEST overlay
gate1_head / gate2_head     = fresh Xavier uniform, bias zeros
stage_a_best_continuation   = false
```

Scientific interpretation: V1R1 is a fresh retraining comparison, not
fine-tuning `cd2829c1…` on a remediation surface. No repository conflict with
the prior two-stage train contract (same BEST-overlay + fresh-heads pattern).

## Pre-authorization: `RESOLVE_V5_STAGE_A_V1R1_TWO_STAGE_CLASS_WEIGHTS`

Train split only (`n=2531`; `train_split_sha256=d8565270…`;
`train_identity_list_sha256=5a6f98c6…`). Provenance: OBSERVED=1.0,
INFERRED=0.5. Formula unchanged; **do not carry V1R9 weights**.

### Gate 1

| Class | rows | OBSERVED | INFERRED | effective | raw_w | norm_w | final |
|---|---:|---:|---:|---:|---:|---:|---:|
| NO_EVIDENCE | 1285 | 255 | 1030 | 770.0 | 1.00064914 | 1.00064851 | **1.0006485087033488** |
| POSSIBLE_EVIDENCE | 1246 | 298 | 948 | 772.0 | 0.99935212 | 0.99935149 | **0.9993514912966515** |

Gate1 row total = 2531.

### Gate 2 (PRESENT+UNCERTAIN only; NONE excluded)

| Class | rows | OBSERVED | INFERRED | effective | raw_w | norm_w | final |
|---|---:|---:|---:|---:|---:|---:|---:|
| UNCERTAIN | 132 | 132 | 0 | 132.0 | 1.71004164 | 1.37537624 | **1.375376244120633** |
| CONFIRMED_PRESENT | 1114 | 166 | 948 | 640.0 | 0.77661123 | 0.62462376 | **0.6246237558793669** |

Gate2 row total = 1246 = train(PRESENT)+train(UNCERTAIN).
Gate2 eligible identity-list SHA == Gate1 POSSIBLE_EVIDENCE identity-list SHA
(`a0bb5d00…`).

```text
CLASS_WEIGHT_ARTIFACT_SHA256 = 80b7f899…
V1R1_TWO_STAGE_CLASS_WEIGHTS.json sealed under private auth dir
```

Literal weights are embedded in the resolved training config; the train runner
must verify the weight-artifact SHA and **must not recompute**.

## Split pins (sealed V1R1; no regenerate)

| Field | Value |
|---|---|
| TRAIN_ROWS | 2531 |
| VALIDATION_ROWS | 1054 |
| TRAIN_SPLIT_SHA256 | `d8565270…` |
| VALIDATION_SPLIT_SHA256 | `3b8d588d…` |
| TRAIN_IDENTITY_LIST_SHA256 | `5a6f98c6…` |
| VALIDATION_IDENTITY_LIST_SHA256 | `8264c946…` |

## Pins

| Field | Value |
|---|---|
| Architecture receipt | `631427cc…` |
| Dataset | `4095036e…` |
| Readiness | `c4b5fc07…` |
| Surface receipt | `3dbdd9b2…` |
| MODEL_WIDE_BEST | `9fba0f66…` |
| Parent STAGE_A_BEST (ref only) | `cd2829c1…` |
| TRAINING_CONFIG_SHA256 | `1527ae18…` |
| AUTHORIZATION_RECEIPT_SHA256 | `f7d4f3ad…` |
| CLASS_WEIGHT_ARTIFACT_SHA256 | `80b7f899…` |
| TRAINING_RUN_LIMIT | 1 |

## Architecture / loss (frozen; unchanged)

- Shared ModernBERT; CLS pool; Gate1/Gate2 linear 2-logit heads
- Trainable: last 2 encoder layers + both heads
- No MLP / retrieval / family head / focal
- `L_total = L_gate1 + 1.0 * L_gate2`; binary weighted CE with sealed V1R1 weights
- Opt: AdamW lr=2e-5 wd=0.01 batch=8 accum=1 epochs=12 min=4 patience=4
  warmup=0.05 clip=1.0 seed=42 max_len=64
- Sampler: full-pass deterministic shuffle; replacement/oversample/undersample/
  class-balanced = false; each epoch consumes all 2531 train rows once

## Acceptance / thresholds

Unchanged end-to-end gates:

```text
false_evidence_entry_rate_on_none <= 0.05
EVIDENCE_PRESENT recall >= 0.70
NO_EVIDENCE recall >= 0.90
```

Threshold grid: Gate1 × Gate2 = 100 pairs
`{0.50…0.95} × {0.50…0.95}`. Prior `0.75/0.50` is **not** carried as mandatory
runtime thresholds. Selection among passing pairs: maximize e2e macro-F1 →
PRESENT recall → UNCERTAIN recall → minimize false-entry → higher Gate1 →
higher Gate2. None pass → `SETTLED_FAIL`. Spent reserve forbidden for
threshold search / checkpoint / early stopping / diagnostics index.

Checkpoint: `0.5*G1_macroF1 + 0.5*G2_macroF1`; tie-break lower Gate1
false-entry → higher Gate2 PRESENT recall → earlier epoch.

## Diagnostics (report-only unless frozen gate says otherwise)

Boundary cells: SHORT_ATOM / DEFINITION_STYLE / PROSE / ORDINARY_PROSE ×
NONE|PRESENT. Slices: provenance, source family, domain, length band,
label authority.

## Private auth dir

`/home/morpheus/hlx-private/classification-v5-stage-a-two-stage-generalization-train-v1-20261001`

## Next action

```text
NEXT_ACTION = TRAIN_V5_STAGE_A_TWO_STAGE_GENERALIZATION_ONCE
```

Stop. Do not train in this execution.

Receipt: `classification-v5-stage-a-two-stage-generalization-authorize-receipt-20261001.json`
(`f7d4f3ad…`).
