# Classification v5 — Repair ident-filtered factorized checkpoint serialization

```text
RULE = REPAIR_IDENT_FILTERED_FACTORIZED_CHECKPOINT_SERIALIZATION
EXPERIMENT = HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-001
CHECKPOINT_REPAIR = FAIL
REPAIR_STATUS = REPAIR_NOT_POSSIBLE_WITHOUT_RETRAIN
PROMOTION_LOADABLE = false
STAGE_A_BEST = cd2829c1… UNCHANGED
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
SCIENTIFIC_RESULT = SETTLED_PASS (preserved; source = original settled run)
SELECTED_EPOCH = 11
INCOMPLETE_SELECTED_CHECKPOINT = 8b2de447…
receipt = 6b04194718f7cbe9645816c7cf9064419f5759d2080bf4bad9c2093281b4d15b
NEXT_ACTION = AUTHORIZE_REPRODUCE_IDENT_FILTERED_FACTORIZED_TRAIN
```

## Repair preflight

| Check | Result |
|---|---|
| Scientific result | `SETTLED_PASS` (train receipt `4a7d565c…`) |
| Promotion state | `PROMOTION_INVALID` (`1123d70d…`) |
| Root cause | `CHECKPOINT_SERIALIZATION_DROPPED_FACTORIZED_HEADS` |
| MODEL_WIDE_BEST | `9fba0f66…` unchanged |
| STAGE_A_BEST | `cd2829c1…` unchanged |
| V1R2 / thresholds | unchanged (`0.60` / `0.75`) |
| Reserve | `HYPERLEX_V5_PROMOTION_RESERVE_001` remains `SPENT` / unused |

Selected-epoch identity verification **passed** against pins:

```text
EXPERIMENT_ID = HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-001
selected_epoch = 11
selected_encoder_sha = 8b2de447…
dataset = 492ed367…
training_config = e252f1ba…
authorization = 6341d083…
```

## Authoritative selected-head source

Allowed sources A/B/C were scanned on Spark under the private train root and
published selected weights.

| Source class | Available |
|---|---|
| A. retained selected-epoch trainer state before flattening | **no** |
| B. retained in-memory/export artifact with exact heads | **no** |
| C. deterministic selected-epoch state artifact with exact heads | **no** |

Scan result:

```text
hit_count = 0
NO_LIVE_TRAINER = true
extras (.pt/.pkl/.bin) = []
```

Every retained `model.safetensors` (tmp epoch candidates including epoch 11,
`selected/`, and published selected) is encoder-only:

```text
n_keys = 12
heads = []
epoch-11 / selected / published sha = 8b2de447…
```

Exact selected-epoch `relation_head` / `resolvability_head` tensors do **not**
exist in retained artifacts. Reconstruction was not attempted. No candidate was
manufactured.

## Serialization whitelist (permanent)

`save_pretrained._HEAD_NAMES` / `FACTORIZED_HEAD_NAMES` permanently include:

```text
relation_head
resolvability_head
```

`flatten_weight_tensors` preserves both heads. `require_factorized_heads_in_flat`
/ `assert_factorized_heads_in_flat` fail closed on missing or wrong-shaped heads.
Ident-filtered train saves now assert heads before `save_file`.

Regression tests:
`tests/shadow/test_classification_v5_stage_a_ident_filtered_checkpoint_repair.py`.

## Historical incomplete checkpoint

```text
8b2de447…
  status = SCIENTIFIC_SELECTED_STATE_REFERENCE
  promotability = NON_PROMOTABLE_PACKAGING_ARTIFACT
  deleted = false
```

Not overwritten. Not promotable packaging.

## Pointer / scientific status

| Field | Value |
|---|---|
| CHECKPOINT_REPAIR | `FAIL` |
| PROMOTION_LOADABLE | `false` |
| STAGE_A_BEST mutated | `false` |
| MODEL_WIDE_BEST mutated | `false` |
| SCIENTIFIC_RESULT | `SETTLED_PASS` |
| SCIENTIFIC_RESULT_SOURCE | `original settled run` |

## Exact next action

```text
AUTHORIZE_REPRODUCE_IDENT_FILTERED_FACTORIZED_TRAIN
```

Do **not** retrain automatically. Do **not** retry promote until a separately
authorized reproduction run produces a complete loadable factorized checkpoint
with exact selected-epoch head identity (or a newly authorized selected epoch).
