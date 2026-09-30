# Classification v5 — diagnose Stage-A-004 SETTLED_FAIL (V1R9)

```text
EXPERIMENT_ID = HLX-CLASSIFICATION-V5-STAGE-A-004
TRAIN = false
RESERVE_CONSUMED = false
BEST_MUTATED = false
PRIMARY_DIAGNOSIS = RESIDUAL_PRESENT_RECALL_FAILURE
CONTROLLED_INTERPRETATION = INSUFFICIENT_MATCHED_SUPPORT
```

Read-only audit of SELECTED checkpoint `82840630…` on READY V1R9 validation
(`8d4be830…`). Diagnostic decisions use the sealed fail-display pair
`none=0.50 / present=0.55` (threshold search not reopened). Parent diagnosis
`MIXED_UNCERTAIN_SURFACE_FAILURE`.

## Error cohorts

| Cohort | n |
|---|---|
| ORDINARY_DOMAIN_FALSE_PRESENT | 15 |
| OTHER_NONE_FALSE_PRESENT | 5 |
| PRESENT_FALSE_NONE | 254 |
| PRESENT_FALSE_UNCERTAIN | 9 |
| UNCERTAIN_MISCLASSIFIED | 162 |

False PRESENT is small in absolute terms (`20` total); ordinary-domain share
`15/20 = 75%` but the false-entry gate already clears (`0.016 ≤ 0.05`).

## Counterfactual gate accounting

Under frozen diagnostic thresholds:

| Gate | Need |
|---|---|
| false_entry ≤ 0.05 | **0** false PRESENT → non-PRESENT (already met) |
| PRESENT recall ≥ 0.70 | recover **72** PRESENT false negatives |
| NONE recall ≥ 0.90 | already met |

## Controlled OBSERVED vs INFERRED

Rule: `HYPERLEX_V5_STAGE_A_CONTROLLED_COMPARISON_V1`.

- Matched-pair coverage `0.126` → **`INSUFFICIENT_MATCHED_SUPPORT`** (<0.60)
- Raw false-entry Δ (OBS−INF) `+0.021`; controlled `+0.016` (not independently causal)

## Label provenance

All `396` misclassified OBSERVED rows classify as `LABEL_PROVENANCE_CLEAN`
under the sealed schema. Failure is not schema invalidity.

## Decision

```text
PRIMARY_DIAGNOSIS = RESIDUAL_PRESENT_RECALL_FAILURE
dataset_change_justified = false
architecture_change_justified = true
```

Smallest remediation: recover ≥72 PRESENT FNs under sealed thresholds; prefer
architecture/objective investigation over another ordinary-NONE dataset
remediation loop. V1R9 UNCERTAIN surface remediation already ran; gold-UNCERTAIN
remain invisible under `P(PRESENT)`-only fail-display policy (162/162).

## Next action

```text
NEXT_ACTION = ARCHITECTURE_OR_OBJECTIVE_INVESTIGATION
```

Stop. Do not train, remediate V1R9 again, retune thresholds, consume reserve,
promote, move BEST, or launch Stage B in this execution.

Receipt: `classification-v5-stage-a-diagnose-v1r9-settled-fail-receipt-20260930.json`
(`96871251…`).
