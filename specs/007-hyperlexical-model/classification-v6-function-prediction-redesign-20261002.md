# REDESIGN_V6_FUNCTION_PREDICTION

```text
OUTCOME = V6_FUNCTION_PREDICTION_PARTIAL
NEXT_ACTION = REASSESS_V6_FUNCTION_TASK_SIGNAL
selected = INDEPENDENT_BINARY_VERIFIERS

DEV_V3 FUNCTION:
  independent = 0.3468
  hybrid      = 0.3286
  semantic    = 0.2039

REP_V3 candidate (INDEPENDENT_BINARY_VERIFIERS):
  system = 0.3302
  DOMAIN = 0.3548   # unchanged (frozen old head)
  FUNCTION = 0.2938
  MEDIATION = 0.3421  # unchanged
  positive-only = 0.3608
  zero-FP = 0.1082
  zero-exact = 0.8918

sealed baseline REP_V3 old heads:
  FUNCTION = 0.2964
  system = 0.3311
  positive-only = 0.3581

Δ FUNCTION = -0.0026
Δ system = -0.0009
Δ positive-only = +0.0027
```

## Formulations tested

1. **INDEPENDENT_BINARY_VERIFIERS** (selected on DEV) — four separate
   binary MLPs with hard-negative strata (other-function, adjacent,
   domain-only, zero-label). NO_FUNCTION = all-off.
2. **FUNCTION_SEMANTIC_MATCHING** — cosine to frozen ontology definitions +
   per-label affine calibration.
3. **HYBRID_VERIFIER** — `[text; def; text⊙def]` → per-function binary MLP.

## Per-function (REP candidate)

| label | P | R | F1 | support |
|---|---:|---:|---:|---:|
| conflictive_force | 0.30 | 0.35 | 0.326 | 62 |
| relational_intimacy | 0.41 | 0.31 | 0.349 | 49 |
| memetic_form | 0.17 | 0.61 | 0.262 | 46 |
| evaluative_stance | 0.19 | 0.31 | 0.239 | 51 |

By source: wikt 0.544 · encyclopedic 0.228  
By length: short 0.559 · medium 0.520 · long 0.364

## Error tradeoffs

Independent verifiers lift recall (esp. memetic) but raise FP, so macro-F1
stays within ~0.003 of the old shared four-output head. DOMAIN/MEDIATION
metrics match the frozen control exactly. NONE operating gates still pass.

## Advancement

Advance required FUNCTION ≥ 0.326 (= 0.296 + 0.03). Not met.
Selected component retained as diagnostic artifact only — **not** promoted
over the old function head.

DOMAIN/MEDIATION heads unchanged. Encoder + ANY_LABEL gate frozen.
QUAL-003 blocked. MODEL_WIDE_BEST unchanged.
