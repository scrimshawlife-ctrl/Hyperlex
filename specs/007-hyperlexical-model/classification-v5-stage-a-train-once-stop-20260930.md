# Classification v5 — Stage A train-once STOP

```text
INPUT_IDENTITY = PASS
SURFACE_READINESS = PASS
TRAINING_CONFIG = MISSING
TRAIN_AUTHORIZED = false
TRAINING_STATUS = NOT_STARTED
SCIENTIFIC_RESULT = NOT_COMPUTABLE
BEST_MUTATED = FALSE
RESERVE_CONSUMED = FALSE
```

## Verified inputs

| Pin | Value |
|---|---|
| code revision | `fab24e4` |
| dataset SHA256 | `a81ca68ad3310981c60d2500a83a0989adeb967cbee6ad6dff003ed2c705efa9` |
| receipt SHA256 | `f07e4c04708bdb0e0e58f91e11d393f852356822f0d9531336667af25b713a40` |
| gate_eval SHA256 | `0a4ad7871351f592371aa93e44207b19039949c4acc598daf69e8b225217af11` |
| surface state | `READY` (all 12 frozen readiness gates pass) |
| BEST | `9fba0f66…` UNCHANGED |

## Why training did not start

`HYPERLEX_CLASSIFICATION_V5_STAGE_A_TRAIN_V1` currently freezes **model
acceptance gates only**:

```text
false_evidence_entry_rate_on_none_max = 0.05
EVIDENCE_PRESENT_recall_min = 0.70
NO_EVIDENCE_recall_min = 0.90
```

It does **not** freeze a training recipe. Missing from the repo:

- `scripts/shadow/hyperlexical/classification_v5_stage_a.py` (or equivalent)
  with frozen `TRAIN_HYPERPARAMS` / threshold grid / promotion criteria wiring
- `scripts/spark/run_classification_v5_stage_a_train.py` (or equivalent)
- resolved config SHA256 for architecture, optimizer, LR, batch size, epochs,
  seed, class weighting, sampling, loss, tokenizer, decision thresholds
- `train_authorized = true` on the Stage-A train contract

V3 Stage A has a frozen recipe (`TRAIN_HYPERPARAMS` in
`classification_v3_stage_a.py`), but that contract is explicitly
`HYPERLEX_CLASSIFICATION_V3_STAGE_A_TRAIN_V1` and is not authorized as the V5
recipe. Copying it would invent a V5 config after seeing READY.

Per the execution contract: if no canonical V5 Stage A recipe exists, **STOP**
rather than invent one.

## What must be sealed before `TRAIN_V5_STAGE_A_ONCE`

```text
AUTHORIZE_V5_STAGE_A_TRAIN_V1
```

That pass should:

1. freeze the complete resolved training config + SHA256;
2. freeze validation/promotion criteria (reuse acceptance gates above; do not
   invent new ones after training);
3. set `train_authorized = true` on the train contract for dataset
   `a81ca68a…`;
4. leave BEST / reserve / readiness thresholds untouched.

Only then is a single training execution scientific.

## Non-actions taken

- no dataset modification
- no readiness-threshold modification
- no surface remediation
- no training launch
- no reserve consumption
- no BEST mutation
