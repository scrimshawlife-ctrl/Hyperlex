# Classification v5 — authorize Stage-A-003 focal objective

```text
MODE = SPECIFY → TEST IMPLEMENTATION → FREEZE → AUTHORIZE → STOP
TRAIN = false
EXPERIMENT_ID = HLX-CLASSIFICATION-V5-STAGE-A-003-FOCAL-LOSS
PARENT = HLX-CLASSIFICATION-V5-STAGE-A-002
OBJECTIVE_STATE = FROZEN
TRAINING_AUTHORIZATION = AUTHORIZED_V5_STAGE_A_003_FOCAL_LOSS_ONCE
```

Preserves the prior blocked preflight
(`classification-v5-stage-a-003-focal-loss-blocked-receipt-20260930.json`)
in the provenance chain: **003 had zero training exposure before this freeze**.

## Frozen objective

| Field | Value |
|---|---|
| `FOCAL_GAMMA` | **2.0** |
| `FOCAL_ALPHA_POLICY` | **NONE** |
| Class weights | UNCHANGED_FROM_STAGE_A_002 |
| Provenance multipliers | UNCHANGED_FROM_STAGE_A_002 |
| Reduction | MEAN_OVER_VALID_EXAMPLES |
| Masking | UNCHANGED_FROM_STAGE_A_002 |
| Decision policy | UNCHANGED `decide_evidence` (P(PRESENT) only) |

Formula:

```text
base_ce_i = class_weight[y] * provenance_multiplier[i] * (-log p_t)
focal_i  = (1 - p_t)^2 * base_ce_i
batch    = mean(focal_i)
```

No focal alpha. Experiment-scoped exception only — canonical Stage-A recipe
still forbids focal globally.

## Implementation tests

| Test | Status |
|---|---|
| GAMMA_ZERO_EQUIVALENCE | PASS |
| EASY_EXAMPLE_DOWNWEIGHT | PASS |
| HARD_EXAMPLE_EMPHASIS | PASS |
| CLASS_WEIGHT_PRESERVATION | PASS |
| PROVENANCE_WEIGHT_PRESERVATION | PASS |
| FINITE_LOSS_EXTREME_LOGITS | PASS |

## Single-factor diff

`SINGLE_FACTOR_DIFF_STATUS = PASS`. Only `OBJECTIVE_CHANGED = TRUE`.

## Hashes

| Artifact | SHA256 |
|---|---|
| `FOCAL_LOSS_SPEC_SHA256` | `dce6dbf5…` |
| `TRAINING_CONFIG_SHA256` | `b8aad3ba…` |
| `CODE_REVISION` | `d58e078f…` |
| Authorization receipt | `e3493590…` |

Repo artifacts:
`artifacts/experiments/HLX-CLASSIFICATION-V5-STAGE-A-003-FOCAL-LOSS/`.

Private auth:
`hlx-private/classification-v5-stage-a-train-v1r8-003-focal-20260930/`
(does not overwrite Stage-A-002).

## Support / falsification (unchanged intent; ordinary-FP bound frozen)

Ordinary false-PRESENT “remains low” frozen as
`ORDINARY_NONE_FALSE_PRESENT <= 22` (2× Stage-A-002 remediated count 11;
pre-V1R8 was 60).

```text
UNCERTAIN_POLICY_INVESTIGATION_PENDING = TRUE
H1_OBJECTIVE_LOSS_PRESSURE = NOT_TESTED
BEST = UNCHANGED
RESERVE = unused
NEXT_ACTION = TRAIN_V5_STAGE_A_003_FOCAL_LOSS_ONCE
STOP.
```
