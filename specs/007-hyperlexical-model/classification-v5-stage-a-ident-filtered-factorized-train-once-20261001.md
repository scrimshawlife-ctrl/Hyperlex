# Classification v5 — Train ident-filtered factorized Stage-A once

```text
RULE = TRAIN_STAGE_A_IDENT_FILTERED_FACTORIZED_ONCE
EXPERIMENT = HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-001
SURFACE = V1R2 / 492ed36751c7fdc4…
ANNOTATIONS = 95d5436555da33ef…
EXCLUSION = 661c9edb095f7f7d…
AUTHORIZATION = 6341d0831327bdc3…
OBJECTIVE = HYPERLEX_V5_STAGE_A_FACTORIZED_RELATION_OBJECTIVE_V1
SCIENTIFIC_RESULT = SETTLED_PASS
SELECTED_CHECKPOINT = 8b2de4472dc0ebd6…
RUN_RECEIPT = 4a7d565ca607234c…
restored_epoch = 11
selection_score = 0.9673
n_threshold_passing = 100 / 100
thresholds = relation 0.60 / resolvability 0.75
STAGE_A_BEST = cd2829c1… UNCHANGED
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
V1R2_MUTATED = false
RESERVE = SPENT / unused
NEXT_ACTION = PROMOTE_STAGE_A_IDENT_FILTERED_FACTORIZED_CANDIDATE
```

Single authorized fresh retrain from MODEL_WIDE_BEST under the unchanged
factorized relation/resolvability objective, on the identifiability-filtered
V1R2 surface only. Excluded identities not restored. No input expansion.

## End-to-end @ selected 0.60 / 0.75

| Gate | Value | Pass |
|---|---:|---|
| false_entry on NONE | 0.034 | yes (≤0.05) |
| EVIDENCE_PRESENT recall | 0.951 | yes (≥0.70) |
| NO_EVIDENCE recall | 0.965 | yes (≥0.90) |
| stage_a_macro_F1 | 0.960 | — |
| UNCERTAIN recall | 1.000 | — |

## Read-only compare vs prior factorized (V1R1 SETTLED_FAIL)

| Metric | Prior factorized | Ident-filtered V1R2 |
|---|---:|---:|
| false_entry | 0.180 | **0.034** |
| NONE recall | 0.807 | **0.965** |
| PRESENT recall | 0.888 | **0.951** |
| SHORT_ATOM NONE relation FPR | 0.539 | **0.013** |

Removing non-identifiable gold materially reduced false-positive relation
learning while retaining PRESENT recall.

## SHORT_ATOM diagnostics (validation)

| Cell | n | metric |
|---|---:|---|
| SHORT_ATOM NONE relation FPR | 152 | **0.013** |
| SHORT_ATOM NONE recall | 152 | 0.980 |
| SHORT_ATOM PRESENT relation recall | 4 | 0.750 (LOW_SUPPORT) |

V1R2 retains only 11 SHORT_ATOM PRESENT rows globally (4 in validation).
Do not treat the positive cohort as a stable subgroup guarantee.

## Identifiability slices (validation)

```text
TEXT_IDENTIFIABLE relation rows = 833
genuine UNCERTAIN rows = 15 (recall 1.000)
MODEL_INPUT = text
```

Also sealed: OBSERVED/INFERRED, source family, domain, length band.

## Limitations

```text
DOMAIN_IRRELEVANT_GENERALIZATION = NOT_ESTABLISHED
SHORT_ATOM_POSITIVE_GENERALIZATION = LOW_SUPPORT (n_PRESENT=11)
```

Aggregate gate pass does **not** establish broad short-atom positive
generalization.

## Exact next action

```text
PROMOTE_STAGE_A_IDENT_FILTERED_FACTORIZED_CANDIDATE
```
