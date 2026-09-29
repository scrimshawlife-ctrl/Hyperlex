# Experiment lifecycle

Future SELECT experiments use five states and five commands.

```text
DRAFT -> PREREGISTERED -> READY -> RUNNING -> SETTLED_PASS | SETTLED_FAIL | SETTLED_INVALID
SETTLED_PASS -> PROMOTED
```

`PROMOTED` is not part of experimental settlement. A pass does not move BEST.

Commands:

```text
preregister
preflight
run
settle
promote
```

`preflight` is one pass. A failed check stays `PREREGISTERED` and records a blocking reason. Source design, reserve acquisition, loader verification, admission-only, launch authorization, and threshold authorization are evidence inside that pass, not lifecycle states.

`run` is the first optimizer step, and only from `READY` with operator decision `AUTHORIZE`. `TRAINING_READY` does not authorize it.

`settle` chooses one outcome. A valid run that misses an acceptance gate is `SETTLED_FAIL`. A broken invariant or execution is `SETTLED_INVALID`.

Historical markers still mean what they meant:

```text
TRAINING_READY                 readiness, not authorization
TRAINING_LAUNCH_AUTHORIZED     operator_authorization PASS when decision is AUTHORIZE
RESERVE_FROZEN                 reserve evidence
ZERO_INIT_LOADER_VERIFIED      loader evidence
```

Those receipts are not rewritten.

The sealed SELECT-006 chain maps to `READY`. Its next action is `RUN`.

## Default schedule

Comparable runs select `classify_macro_f1_nonnone`. With no preregistered schedule, they use the SELECT-006 candidate schedule: max 12 epochs, minimum 4, patience 4, strict improvement, ties keep the earlier checkpoint, and restore best.

A preregistered schedule replaces that default. The sealed SELECT-006 control schedule, 40 epochs with early stopping off, remains that kind of override. Unset unbind runs stay at 2 epochs with early stopping off.
