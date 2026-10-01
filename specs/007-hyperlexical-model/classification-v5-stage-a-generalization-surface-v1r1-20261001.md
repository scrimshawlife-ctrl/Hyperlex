# Classification v5 — Stage-A generalization surface V1R1

```text
ACTION = REMEDIATE_V5_STAGE_A_GENERALIZATION_SURFACE_GATES
surface = HYPERLEX_V5_STAGE_A_GENERALIZATION_SURFACE_V1R1
surface_version = classification-v5-stage-a-generalization-surface-v1r1-20261001
parent = classification-v5-stage-a-generalization-surface-v1-20261001
parent_sha256 = 7567edcdf74c1033a07e3ae1d42b0e54ed0804b78fd7ba340c35752ac13df09f
dataset_sha256 = 4095036e5af3ad7cfe9f038dd3e1f46e4ef0ea18db4c4b7186fc2b02e96d4274
state = READY
strategy = FRESH_NON_WIKTIONARY_MATCHED_CONTRAST_ADDITIONS
STAGE_A_BEST = cd2829c1… UNCHANGED
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
spent_reserve = HYPERLEX_V5_PROMOTION_RESERVE_001 SPENT/IMMUTABLE (overlap=0)
TRAIN = false
receipt = 3dbdd9b2…
next_action = AUTHORIZE_V5_STAGE_A_TWO_STAGE_RETRAIN_ON_GENERALIZATION_SURFACE
```

Successor of sealed PREREGISTERED V1. Parent artifact not mutated. Single
constrained remediation via fresh non-Wiktionary matched contrasts.

## Delta

| | n |
|---|---:|
| previous (V1) | 2624 |
| retained | 2624 |
| added | 961 |
| removed | 0 |
| successor total | 3585 |

Train 2531 / validation 1054. PRESENT 1535 / NONE 1851 / UNCERTAIN 199.

## Failed-gate repair (before → after)

| Metric | V1 | V1R1 |
|---|---:|---:|
| SHORT_ATOM NONE train | 114 | 158 |
| SHORT_ATOM PRESENT train | 113 | 170 |
| wik share PRESENT | 0.2788 | 0.2221 |
| wik share NONE | 0.2737 | 0.1777 |
| median token ratio | 1.385 | 0.938 |
| top100 Jaccard | 0.235 | 0.493 |
| length-only BA | 0.621 | 0.552 |
| TF-IDF BA | 0.772 | 0.748 |

All frozen readiness gates: **PASS**. State: **READY**.

## Exact next action

```text
AUTHORIZE_V5_STAGE_A_TWO_STAGE_RETRAIN_ON_GENERALIZATION_SURFACE
```

Do not train in this remediation pass.
