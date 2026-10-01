# Classification v5 — Diagnose factorized relation SETTLED_FAIL

```text
RULE = DIAGNOSE_STAGE_A_FACTORIZED_RELATION_SETTLED_FAIL
EXPERIMENT = HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-001
FAILED_CHECKPOINT = 8a6981c1…
PRIMARY_DIAGNOSIS = MODEL_INPUT_INFORMATION_DEFICIT
NEXT_ACTION = REVISE_GOLD_IDENTIFIABILITY_CONTRACT
DATASET_CONSEQUENCE = GOLD_CONTRACT_REPAIR_REQUIRED
STAGE_A_BEST = cd2829c1… UNCHANGED
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
TRAIN = false
receipt = 827c0e2be1619def…
```

Read-only. No train, relabel, surface, threshold, Stage-B, reserve, or BEST moves.

## Frozen observed outcome

| Metric | Value |
|---|---:|
| threshold pairs passing | 0 / 100 |
| false_entry | 0.180 |
| NONE recall | 0.807 |
| PRESENT recall | 0.888 |
| SHORT_ATOM NONE relation FPR | 0.539 |
| SHORT_ATOM PRESENT relation recall | 0.750 |

## Cross-experiment SHORT_ATOM geometry

| Model | centroid cos | linear BA | nonlinear BA | NONE FPR (native/linear) | PRESENT recall |
|---|---:|---:|---:|---|---:|
| MODEL_WIDE_BEST | 0.981 | 0.622 | 0.619 | None/0.474 | 0.718 |
| STAGE_A_BEST | 0.973 | 0.613 | 0.616 | 0.461/0.474 | 0.609 |
| TWO_STAGE_FAILED_26841d5f | 0.975 | 0.587 | 0.596 | 0.546/0.500 | 0.750 |
| FACTORIZED_FAILED_8a6981c1 | 0.975 | 0.570 | 0.596 | 0.539/0.533 | 0.750 |

## Displacement class

```text
reshaped_but_not_label_separating
```

Factorized vs prior two-stage embedding displacement mean ≈ 0.003 (geometry essentially unchanged by objective change).

## Layer-wise finding

```text
best_layer = 13
last_layer = 22
best_BA = 0.657
last_BA = 0.570
best_minus_last_delta = 0.087
layer_finding = NO_LAYER_SEPARATES
adaptation_depth = DEEPER_ADAPTATION_NOT_SUPPORTED
```

## Pooling / token

```text
pooling_finding = POOLING_NOT_PRIMARY
token_finding = TOKEN_SIGNAL_ABSENT
cls_BA = 0.570
token_BA = 0.545
best_alt_pooling = first_content (0.584)
```

## Identifiability / collisions

| Item | n |
|---|---:|
| exact PRESENT/NONE text collisions | 0 |
| SHORT_ATOM exact PRESENT/NONE | 0 |
| SHORT_ATOM near PRESENT/NONE | 0 |
| REQUIRES_EXTERNAL_CONTEXT (val SA) | 152 |
| TEXT_IDENTIFIABLE (val SA) | 122 |

Metadata subtype BA gain: **0.430** (embedding-only 0.570 → embedding+subtype 1.000). Diagnostic only — do not treat subtype as production input.

## Irreducible-overlap test

```text
IRREDUCIBLE_SEMANTIC_OVERLAP checks all true under text-only recovery paths,
but subtype/metadata recovers BA=1.0 → primary is MODEL_INPUT_INFORMATION_DEFICIT
(not STOP under irreducible text overlap alone).
```

## Primary diagnosis / next action

```text
PRIMARY_DIAGNOSIS = MODEL_INPUT_INFORMATION_DEFICIT
DATASET_CONSEQUENCE = GOLD_CONTRACT_REPAIR_REQUIRED
architecture_change_justified = False
input_contract_change_justified = True
NEXT_ACTION = REVISE_GOLD_IDENTIFIABILITY_CONTRACT
NEXT_ACTION_AUTHORIZED = false
```

Do **not** authorize the next action here.
