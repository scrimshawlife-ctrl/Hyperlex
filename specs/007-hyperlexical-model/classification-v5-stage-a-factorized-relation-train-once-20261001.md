# Classification v5 — Train factorized relation Stage-A once

```text
RULE = TRAIN_STAGE_A_FACTORIZED_RELATION_ONCE
EXPERIMENT = HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-001
OBJECTIVE = HYPERLEX_V5_STAGE_A_FACTORIZED_RELATION_OBJECTIVE_V1
AUTHORIZATION = 133d8dd0…
SCIENTIFIC_RESULT = SETTLED_FAIL
SELECTED_CHECKPOINT = 8a6981c1…
RUN_RECEIPT = 76b1d5f5…
restored_epoch = 12
selection_score = 0.8757
n_threshold_passing = 0 / 100
STAGE_A_BEST = cd2829c1… UNCHANGED
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
RESERVE = SPENT / unused
NEXT_ACTION = DIAGNOSE_STAGE_A_FACTORIZED_RELATION_SETTLED_FAIL
```

Single authorized fresh retrain from MODEL_WIDE_BEST under the factorized
relation objective. No `POSSIBLE_EVIDENCE` target.

## End-to-end @ fail-display 0.50/0.50 (no passing grid pair)

| Gate | Value | Pass |
|---|---:|---|
| false_entry on NONE | 0.180 | no (≤0.05) |
| EVIDENCE_PRESENT recall | 0.888 | yes (≥0.70) |
| NO_EVIDENCE recall | 0.807 | no (≥0.90) |
| stage_a_macro_F1 | 0.835 | — |
| UNCERTAIN recall | 0.791 | — |

## SHORT_ATOM relation-head diagnostic

| Cell | n | metric |
|---|---:|---|
| SHORT_ATOM NONE relation FPR | 152 | **0.539** |
| SHORT_ATOM PRESENT relation recall | 156 | 0.750 |
| NONE relation score median | — | 0.619 |
| PRESENT relation score median | — | 0.952 |

Direct relation supervision did **not** clear the diagnosed SHORT_ATOM NONE
rejection failure under the sealed acceptance gates.

## Limitation

```text
DOMAIN_IRRELEVANT_GENERALIZATION = NOT_ESTABLISHED
```

## Exact next action

```text
DIAGNOSE_STAGE_A_FACTORIZED_RELATION_SETTLED_FAIL
```
