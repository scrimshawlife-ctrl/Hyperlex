# Classification v5 — Stage-A V1R8 single train (`SETTLED_FAIL`)

Experiment: `HLX-CLASSIFICATION-V5-STAGE-A-002`  
Surface: `HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R8` (`c0fdd82d…`)  
Parent diagnosis: `MIXED_STAGE_A_FAILURE`  
Config: `2ce1b29b…` · seed 42 · restored epoch 10  
SELECTED: `b22e9c20…` · run receipt `c0008f3c…`

## Completion

| Gate | Result |
|---|---|
| PROCESS_EXIT | CLEAN |
| TRAINING_COMPLETE | TRUE |
| SELECTED_CHECKPOINT | PRESENT |
| ARTIFACT_MANIFEST | COMPLETE |
| BEST | UNCHANGED |
| RESERVE | unused |

## Frozen Stage-A acceptance (fail-display 0.50 / 0.55; grid n_passing=0)

| Metric | Value | Threshold | Pass |
|---|---:|---:|:---:|
| false_evidence_entry_rate_on_none | 0.0120 | ≤ 0.05 | yes |
| EVIDENCE_PRESENT recall | 0.5275 | ≥ 0.70 | no |
| NO_EVIDENCE recall | 0.9872 | ≥ 0.90 | yes |

`THRESHOLD_FEASIBLE = false` → **`SETTLED_FAIL`**. `PROMOTION_CANDIDATE = false`.

## Diagnostic cohorts vs parent (same definitions; 0.50 / 0.55)

| Cohort | Parent | V1R8 | Δ |
|---|---:|---:|---:|
| ordinary NONE → PRESENT | 60 | 11 | −49 |
| other NONE → PRESENT | 3 | 4 | +1 |
| PRESENT → NONE | 146 | 297 | +151 |
| PRESENT → UNCERTAIN | 3 | 4 | +1 |
| UNCERTAIN misclassified | 53 | 61 | +8 |

Validation PRESENT support grew (423 → 637), so absolute FN counts are not
size-matched; the authoritative recall comparison is:

| | Parent V1R7 | V1R8 |
|---|---:|---:|
| PRESENT recall | 0.648 | 0.527 |
| false-entry on NONE | 0.069 | 0.012 |

## Both-sides test

- Specificity side: material improvement (ordinary false PRESENT 60→11;
  false-entry gate now passes).
- Recall side: still fails the frozen 0.70 gate and is worse than parent.

**PRIMARY_DIAGNOSIS = `RESIDUAL_PRESENT_RECALL_FAILURE`**

`ARCHITECTURE_CHANGE_JUSTIFIED = false` (no architecture change in this
execution).  
`ARCHITECTURE_OR_OBJECTIVE_INVESTIGATION_JUSTIFIED = true` (another
dataset-remediation loop should not be the automatic next action).

## Next action

```text
NEXT_ACTION = ARCHITECTURE_OR_OBJECTIVE_INVESTIGATION
```

Stop. Do not remediate V1R8 again, train another seed, consume reserve,
change architecture/objective/thresholds, promote, move BEST, or launch
Stage B in this execution.
