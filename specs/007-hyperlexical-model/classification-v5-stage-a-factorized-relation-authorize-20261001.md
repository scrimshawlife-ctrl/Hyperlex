# Classification v5 — Authorize factorized relation Stage-A train

```text
RULE = AUTHORIZE_STAGE_A_FACTORIZED_RELATION_TRAIN
EXPERIMENT = HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-001
OBJECTIVE = HYPERLEX_V5_STAGE_A_FACTORIZED_RELATION_OBJECTIVE_V1
TRAIN_AUTHORIZED = true
TRAINING_STATUS = AUTHORIZED_NOT_STARTED
SCIENTIFIC_RESULT = NOT_COMPUTABLE
TRAINING_RUN_LIMIT = 1
V1R1 = 4095036e…
ANNOTATION = 4ac88450…
CLASS_WEIGHT_ARTIFACT = 47e58773…
TRAINING_CONFIG = 618079c7…
AUTHORIZATION = 133d8dd0…
MODEL_WIDE_BEST = 9fba0f66… (fresh init)
STAGE_A_BEST = cd2829c1… reference only / unchanged
RESERVE = SPENT / unused
NEXT_ACTION = TRAIN_STAGE_A_FACTORIZED_RELATION_ONCE
```

Authorization only. Does not train.

## Split (sealed V1R1)

| Split | n | SHA |
|---|---:|---|
| train | 2531 | `d8565270…` |
| validation | 1054 | `3b8d588d…` |
| train identities | 2531 | `5a6f98c6…` |
| validation identities | 1054 | `8264c946…` |

## Class weights (train only; fresh; not Gate1/Gate2)

### Relation (eligible = 2399; masked AMBIGUOUS = 132)

| Class | rows | OBS | INF | effective | final |
|---|---:|---:|---:|---:|---:|
| NO_EVIDENCE_RELATION | 1285 | 255 | 1030 | 770.0 | 0.9538023229441501 |
| EVIDENCE_RELATION_PRESENT | 1114 | 166 | 948 | 640.0 | 1.0461976770558497 |

### Resolvability (eligible = 2531)

| Class | rows | OBS | INF | effective | final |
|---|---:|---:|---:|---:|---:|
| UNRESOLVABLE | 132 | 132 | 0 | 132.0 | 1.5314299338122987 |
| RESOLVABLE | 2399 | 421 | 1978 | 1410.0 | 0.50 (clipped) |

Masked-relation identity hash == train AMBIGUOUS identity hash.

## Initialization

Fresh retrain from MODEL_WIDE_BEST `9fba0f66…`; last two encoder layers from that overlay; relation/resolvability heads fresh Xavier. Not STAGE_A_BEST continuation.

## Loss / selection / thresholds

```text
L = L_relation + 1.0 * L_resolvability
selection = 0.50*relation_macro_F1 + 0.50*resolvability_macro_F1
thresholds = {0.50…0.95}² (100 pairs; not Gate1/Gate2)
acceptance = FE≤0.05 ∧ PRESENT≥0.70 ∧ NONE≥0.90
```

## Exact next action

```text
TRAIN_STAGE_A_FACTORIZED_RELATION_ONCE
```
