# Classification v5 — diagnose Stage-A SETTLED_FAIL

```text
EXPERIMENT_ID = HLX-CLASSIFICATION-V5-STAGE-A-001
TRAIN = false
RESERVE_CONSUMED = false
BEST_MUTATED = false
PRIMARY_DIAGNOSIS = MIXED_STAGE_A_FAILURE
CONTROLLED_INTERPRETATION = INSUFFICIENT_MATCHED_SUPPORT
```

Read-only audit of SELECTED checkpoint `3b1b574a…` on validation
(`a81ca68a…`). Diagnostic decisions use the sealed fail-display pair
`none=0.50 / present=0.55` (threshold search not reopened).

## Error cohorts

| Cohort | n |
|---|---|
| ORDINARY_DOMAIN_FALSE_PRESENT | 60 |
| OTHER_NONE_FALSE_PRESENT | 3 |
| PRESENT_FALSE_NONE | 146 |
| PRESENT_FALSE_UNCERTAIN | 3 |
| UNCERTAIN_MISCLASSIFIED | 53 |

False PRESENT is almost entirely ordinary-domain (`60/63 = 95.2%`) and
OBSERVED (`62/63 = 98.4%`).

## Controlled OBSERVED vs INFERRED

Rule: `HYPERLEX_V5_STAGE_A_CONTROLLED_COMPARISON_V1`.

| Estimand | Raw Δ (OBS−INF) | Matched Δ | Notes |
|---|---|---|---|
| false_entry | `+0.132` | `+0.120` | CI95 `[0.069, 0.176]` |
| PRESENT recall | `−0.530` | `−0.409` | |
| NONE recall | `−0.137` | `−0.126` | |

- Exact strata: 13 strata; OBS coverage `0.590`, INF `0.562`
- Matched-pair coverage: `0.418` (`matched_n=302`) →
  **`INSUFFICIENT_MATCHED_SUPPORT`** (<0.60)
- Matched false-entry retains ~90% of the raw gap, but coverage forbids
  treating provenance as an independent causal driver under the frozen rule.

Sequential decomposition (false-entry residual): subtype `0.066` →
+surface/length/style `0.083` → +source/domain/provenance/similarity collapses
strata support (`None` at full F-stage).

## Ordinary-domain NONE

Of 341 validation `ORDINARY_DOMAIN_NONE`:

- false PRESENT = 60, all OBSERVED, 55× `SOURCE_ASSERTED+DIRECT`, 5× pairwise
- mean `P(PRESENT)=0.866`; nearest-positive sim `0.949` ≈ nearest-NONE `0.959`
- topics: zoology/math/physics/anatomy/ornithology Wiktionary shards

## Label provenance

All `215` misclassified OBSERVED rows classify as
`LABEL_PROVENANCE_CLEAN` under the sealed schema. Failure is not schema
invalidity; ordinary-domain SOURCE_ASSERTED negatives remain semantically hard
against slang-like definition prose.

## Counterfactual gate accounting

Under frozen diagnostic thresholds:

| Gate | Need |
|---|---|
| false_entry ≤ 0.05 | fix **18** false PRESENT → non-PRESENT |
| PRESENT recall ≥ 0.70 | recover **23** PRESENT false negatives |
| NONE recall ≥ 0.90 | already met |

## Decision

```text
PRIMARY_DIAGNOSIS = MIXED_STAGE_A_FAILURE
dataset_change_justified = true
architecture_change_justified = false
```

Smallest remediation: jointly remediate OBSERVED ordinary-domain NONE
acquisition and source/domain skew; defer architecture change. No retrain on
the unchanged surface.

## Exact next action

```text
REMEDIATE_V5_STAGE_A_MIXED_FAILURE
```
