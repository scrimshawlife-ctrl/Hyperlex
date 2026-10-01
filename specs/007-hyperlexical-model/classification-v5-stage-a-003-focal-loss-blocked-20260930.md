# Classification v5 — Stage-A-003 focal-loss blocked (unfrozen objective)

```text
EXPERIMENT_ID = HLX-CLASSIFICATION-V5-STAGE-A-003-FOCAL-LOSS
PARENT = HLX-CLASSIFICATION-V5-STAGE-A-002
TRAINING_STATUS = BLOCKED_UNFROZEN_OBJECTIVE
TRAIN = false
BEST = UNCHANGED
RESERVE = unused
```

## Parent verification (PASS)

| Pin | Observed |
|---|---|
| SPECIFICITY_FAILURE_REMEDIATED | TRUE |
| false_evidence_entry_rate_on_none | `0.012` (PASS) |
| PRESENT_RECALL | `0.527` (FAIL) |
| THRESHOLD_GRID_N_PASSING | `0` |
| PRESENT_TO_NONE_N | `297` |
| PRESENT_TO_NONE_MEDIAN_P_NONE | `0.994` |
| PRESENT_TO_NONE_CONFIDENT_NONE_FRAC | `0.747` |
| PRESENT_TO_NONE_NEAR_BOUNDARY_FRAC | `0.010` |
| PROMOTION | FAIL |
| DATASET_SHA256 | `c0fdd82d…` |
| BEST | UNCHANGED |
| RESERVE | unused |

## Single-factor intent (acknowledged, not executed)

Intended change: weighted CE → class-weighted focal CE only.
Held fixed: V1R8, splits, seed 42, ModernBERT, head, pooling, tokenizer,
optimizer/LR/batch/epochs/scheduler, class weights, provenance multipliers,
sampling, `decide_evidence`, threshold grid, evaluation code.

## Block reason

Section 3 of the Stage-A-003 mission requires the focal-loss recipe to be
**already frozen** before training, including `FOCAL_GAMMA`.

Authoritative search found:

| Artifact | Focal status |
|---|---|
| Parent 002 `RESOLVED_TRAINING_CONFIG.json` | `loss.name=weighted_cross_entropy`; `focal` listed under `loss.forbidden` |
| Investigation receipt | recommends focal; says “freeze gamma in recipe”; **does not set a numeric gamma** |
| Repo / private Spark artifacts | **no** `FOCAL_GAMMA`, `FOCAL_LOSS_SPEC`, or frozen focal semantics |

Per mission rule: do not invent a convenient gamma during execution.

```text
TRAINING_STATUS = BLOCKED_UNFROZEN_OBJECTIVE
FOCAL_GAMMA = NOT_COMPUTABLE
FOCAL_LOSS_SPEC_SHA256 = NOT_COMPUTABLE
FOCAL_LOSS_IMPLEMENTATION_TEST = NOT_RUN
SCIENTIFIC_RESULT = NOT_COMPUTABLE
```

## What must be frozen before retry

A sealed authorize / objective-spec step must preregister, at minimum:

- `FOCAL_GAMMA` (single numeric value; no sweep)
- `FOCAL_ALPHA_POLICY` (none / fixed / class-weight-as-alpha)
- `CLASS_WEIGHT_POLICY` (identical to parent 002)
- `PROVENANCE_MULTIPLIER_POLICY` (identical to parent 002)
- `REDUCTION` (e.g. mean over unmasked token/example losses)
- masking / ignore behavior identical to parent
- numerical definition: `(1-p_t)^γ * CE` with class×provenance weights applied as in parent

Only after that seal may implementation tests + one train proceed.

## Protection

No train. No dataset change. No `decide_evidence` change. No head/hierarchy/
backbone change. No gamma invention. Reserve unused. BEST unchanged.

```text
NEXT_ACTION = AUTHORIZE_V5_STAGE_A_003_FOCAL_LOSS_OBJECTIVE
STOP.
```
