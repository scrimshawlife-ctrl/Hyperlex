# Classification v5 — Stage-A V1R9 single train (`SETTLED_FAIL`)

Experiment: `HLX-CLASSIFICATION-V5-STAGE-A-004`  
Surface: `HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R9` (`8d4be830…`)  
Parent diagnosis: `MIXED_UNCERTAIN_SURFACE_FAILURE`  
Parent experiment: `HLX-CLASSIFICATION-V5-STAGE-A-002` (V1R8)  
Config: `0c9df174…` · seed 42 · restored epoch 12  
SELECTED: `82840630…` · run receipt `a03bc46a…`

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
| false_evidence_entry_rate_on_none | 0.0160 | ≤ 0.05 | yes |
| EVIDENCE_PRESENT recall | 0.5871 | ≥ 0.70 | no |
| NO_EVIDENCE recall | 0.9832 | ≥ 0.90 | yes |

`THRESHOLD_FEASIBLE = false` → **`SETTLED_FAIL`**. `PROMOTION_CANDIDATE = false`.

## Diagnostic cohorts vs parent Stage-A-002 (same definitions; 0.50 / 0.55)

| Cohort | Parent V1R8 | V1R9 | Δ |
|---|---:|---:|---:|
| ordinary NONE → PRESENT | 11 | 15 | +4 |
| other NONE → PRESENT | 4 | 5 | +1 |
| PRESENT → NONE | 297 | 254 | −43 |
| PRESENT → UNCERTAIN | 4 | 9 | +5 |
| UNCERTAIN misclassified | 61 | 162 | +101 |

Validation UNCERTAIN support grew (61 → 162) after V1R9 remediation, so the
UNCERTAIN misclassified absolute count is not size-matched. Under fail-display
thresholds gold-UNCERTAIN recall remains **0** (policy still `P(PRESENT)`-only).

Authoritative gate comparison:

| | Parent V1R8 | V1R9 |
|---|---:|---:|
| PRESENT recall | 0.527 | 0.587 |
| false-entry on NONE | 0.012 | 0.016 |

## Both-sides test

- Specificity side: still passes frozen false-entry gate (0.016 ≤ 0.05).
- Recall side: improved vs parent (+0.060) but still fails the frozen 0.70 gate.

**PRIMARY_DIAGNOSIS = `RESIDUAL_PRESENT_RECALL_FAILURE`**

`ARCHITECTURE_CHANGE_JUSTIFIED = false` (no architecture change in this
execution).

## Next action

```text
NEXT_ACTION = DIAGNOSE_V5_STAGE_A_SETTLED_FAIL
```

Stop. Do not train another seed, consume reserve, change
architecture/objective/thresholds, promote, move BEST, remediate V1R9 again,
or launch Stage B in this execution.
