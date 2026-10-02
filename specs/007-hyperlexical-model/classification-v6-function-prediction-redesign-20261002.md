# REDESIGN_V6_FUNCTION_PREDICTION

```text
OUTCOME = V6_FUNCTION_PREDICTION_PARTIAL
NEXT_ACTION = REASSESS_V6_FUNCTION_TASK_SIGNAL
selected = INDEPENDENT_BINARY_VERIFIERS

DEV_V3 FUNCTION:
  independent = 0.3468
  semantic    = 0.2039
  hybrid      = 0.3286

REP_V3 candidate (INDEPENDENT_BINARY_VERIFIERS):
  system = 0.3302
  DOMAIN = 0.3548
  FUNCTION = 0.2938
  MEDIATION = 0.3421
  positive-only = 0.3608
  zero-FP = 0.1082
  zero-exact = 0.8918

sealed baseline REP_V3 old heads:
  FUNCTION = 0.2964
  system = 0.3311
  positive-only = 0.3581

Δ FUNCTION = -0.0026
Δ system = -0.0009
```

DOMAIN/MEDIATION heads unchanged. Encoder + ANY_LABEL gate frozen.
QUAL-003 blocked. MODEL_WIDE_BEST unchanged.
