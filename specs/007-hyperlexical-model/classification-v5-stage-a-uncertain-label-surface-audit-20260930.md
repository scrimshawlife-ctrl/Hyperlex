# Classification v5 — UNCERTAIN label-surface audit

Parent SELECTED: `dba6d491…` · V1R8 `c0fdd82d…` · BEST `9fba0f66…` unchanged  
Gold mapping: `HYPERLEX_V5_STAGE_A_GOLD_LABEL_MAPPING_V1`  
Fail-closed contract: missing ≠ NO_EVIDENCE; NO_DATA preserved for zero-support reasons.

```text
AUDIT_STATE = COMPLETE
TRAIN = false
RELABEL = false
PRIMARY_DIAGNOSIS = MIXED_UNCERTAIN_SURFACE_FAILURE
NEXT_ACTION = REMEDIATE_V5_UNCERTAIN_SURFACE
DATA_COMPLETENESS_BLOCKER = False
```

## Support

| Split | n |
|---|---:|
| train | 183 |
| validation | 61 |

### Ambiguity-reason distribution (frozen vocabulary)

| Reason | train | val | state |
|---|---:|---:|---|
| MULTIPLE_PLAUSIBLE_INTERPRETATIONS | 183 | 61 | OBSERVED_VALUE |
| INSUFFICIENT_CONTEXT | 0 | 0 | NO_DATA / UNDER_SUPPORTED |
| CONFLICTING_EVIDENCE | 0 | 0 | NO_DATA / UNDER_SUPPORTED |
| PARTIAL_REQUIRED_CORE | 0 | 0 | NO_DATA / UNDER_SUPPORTED |
| UNRESOLVED_SOURCE_MEANING | 0 | 0 | NO_DATA / UNDER_SUPPORTED |

Provenance: INFERRED 234 / OBSERVED 10 · ATOM 197 / AMBIGUOUS 45 / PROSE 2  
Isolation: `['UNCERTAIN_PROVENANCE_ISOLATED', 'UNCERTAIN_SOURCE_FAMILY_ISOLATED']`

## Gold consistency (flags only; no relabel)

`{'SEMANTICALLY_CLEAN': 77, 'TOO_NONE_LIKE': 77, 'TOO_PRESENT_LIKE': 90}`

Required-field completeness: missing_required_frac=`0.0` · n_missing_rows=`0`

## Representation boundary (frozen BEST CLS)

`{'CENTERED_BETWEEN': 77, 'NONE_LIKE': 77, 'PRESENT_LIKE': 90}`  
coverage=`1.0`

## vs PRESENT FNs (leave-one-out for PRESENT pool)

- GENUINELY_UNCERTAIN (n=39): resembles **gold PRESENT**;
  PRESENT_UNCERTAIN_BOUNDARY_CONFLICT=`False`
- NONE_DOMINATED (n=194): **NONE-like**
  (NONE cos≈0.955 vs UNCERTAIN≈0.892)

## Head signal by reason (SELECTED; scalar 0.50/0.55)

MULTIPLE_PLAUSIBLE_INTERPRETATIONS: mean P(UNC)=`0.804`, top1-UNC=`210/244`,
scalar UNC recall=`0.004` (policy ignores UNC mass). Other reasons: **NO_DATA**.

## Completeness

| Diagnostic | coverage | state |
|---|---:|---|
| ambiguity_reason | 1.0 | OK |
| probability | 1.0 | OK |
| representation | 1.0 | OK |

NO_DATA cohorts: `['INSUFFICIENT_CONTEXT', 'CONFLICTING_EVIDENCE', 'PARTIAL_REQUIRED_CORE', 'UNRESOLVED_SOURCE_MEANING']`  
NOT_COMPUTABLE: definition_style_balance (field not stored)

## Decision

```text
PRIMARY_DIAGNOSIS = MIXED_UNCERTAIN_SURFACE_FAILURE
SMALLEST_JUSTIFIED_REMEDIATION = REMEDIATE_V5_UNCERTAIN_SURFACE
DATASET_CHANGE_JUSTIFIED = true
ARCHITECTURE_CHANGE_JUSTIFIED = false
```

Mixture: four frozen ambiguity reasons have zero support; UNCERTAIN mass is
source/provenance-isolated; gold rows split across PRESENT_LIKE / NONE_LIKE /
CENTERED without a single clean center. No train / relabel / reserve / BEST move.
