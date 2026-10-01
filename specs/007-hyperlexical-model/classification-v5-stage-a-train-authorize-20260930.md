# Classification v5 — AUTHORIZE Stage-A train (`AUTHORIZE_V5_STAGE_A_TRAIN_V1`)

```text
INPUT_IDENTITY = PASS
SURFACE_READINESS = PASS
TRAIN_AUTHORIZED = true
TRAINING_STATUS = AUTHORIZED_NOT_STARTED
SCIENTIFIC_RESULT = NOT_COMPUTABLE
BEST_MUTATED = FALSE
RESERVE_CONSUMED = FALSE
```

## Pins

| Pin | Value |
|---|---|
| rule | `HYPERLEX_CLASSIFICATION_V5_STAGE_A_TRAIN_V1` |
| label provenance | `HYPERLEX_V5_STAGE_A_LABEL_PROVENANCE_V1` |
| experiment ID | `HLX-CLASSIFICATION-V5-STAGE-A-001` |
| dataset SHA256 | `a81ca68ad3310981c60d2500a83a0989adeb967cbee6ad6dff003ed2c705efa9` |
| readiness receipt | `f07e4c04708bdb0e0e58f91e11d393f852356822f0d9531336667af25b713a40` |
| gate_eval | `0a4ad7871351f592371aa93e44207b19039949c4acc598daf69e8b225217af11` |
| CURRENT_BEST | `9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6` |
| surface rule | `HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R7` |
| code revision | `1b0264a6ee484068dbd1b284e8d2ff22789a245b` |
| TRAINING_CONFIG_SHA256 | `4d2eaabd52976da6beecfac1175770a9f3402c82d0b124942638488aa8ab4d7e` |
| AUTHORIZATION_RECEIPT_SHA256 | `f736bf3df3888258173c8d0c596d581e890782d8ebb68a8b171b7ec296e7f00b` |
| AUTHORIZATION.json SHA256 | `4923a9e2939799cbee3b10f0b3c96b0759f5c7b89c2c04865efd28dfdc50805a` |
| label provenance valid | `5877 / 5877` (`invalid=0`) |

Frozen class weights (TRAIN effective counts → sqrt/median → mean-normalize → clip):

| Class | Weight | Effective count |
|---|---|---|
| NO_EVIDENCE | `0.50` (clipped) | `1859.0` |
| EVIDENCE_PRESENT | `0.8786801255199984` | `371.5` |
| UNCERTAIN | `1.7285207441639725` | `96.0` |

Diagnostic: `UNCERTAIN` is 100% from `HYPERLEX_V5_STAGE_A_AMBIGUOUS_V1` (single-rule dominance warning; not a readiness failure).

## Architecture (frozen)

```text
input
  -> frozen/base ModernBERT encoder (init from CURRENT_BEST; do not mutate BEST)
  -> train last 2 encoder layers + linear evidence head (hidden -> 3 logits)
classes (index order):
  0 = NO_EVIDENCE
  1 = EVIDENCE_PRESENT
  2 = UNCERTAIN
```

No family classifier. No retrieval loss. Head init:
`xavier_uniform_bias_zeros`, seed `42`.

## Loss

Weighted cross-entropy only.

- provenance multipliers: `OBSERVED=1.0`, `INFERRED=0.5`
- class weights from TRAIN effective counts:
  `sqrt(median/effective_c)` → mean-normalize → clip `[0.50, 2.00]`
- frozen class weights recorded in `CLASS_WEIGHTS.json`

## Optimization

| Hyperparam | Value |
|---|---|
| optimizer | AdamW |
| learning_rate | `2e-5` |
| weight_decay | `0.01` |
| micro_batch_size | `8` |
| gradient_accumulation | `1` |
| max_epochs | `12` |
| minimum_epochs | `4` |
| early_stopping_patience | `4` |
| warmup_ratio | `0.05` |
| max_grad_norm | `1.0` |
| seed | `42` |
| max_length | `64` |
| truncation | true |
| padding | right |
| pooling | `last_hidden_state[:,0]` |

## Checkpoint selection (validation)

Primary: highest `stage_a_macro_f1`.
Tie-break: lower `false_evidence_entry_rate_on_none`, higher `NO_EVIDENCE`
recall, earlier epoch. Strict improvement. Restore best checkpoint.

## Threshold policy

Decision score = `P(EVIDENCE_PRESENT)`. Grid:
`none_threshold, present_threshold ∈ {0.50…0.95 step 0.05}` with
`none < present`.

```text
if evidence_score >= present_threshold: EVIDENCE_PRESENT
elif evidence_score <= none_threshold: NO_EVIDENCE
else: UNCERTAIN
```

Selection requires all three acceptance gates, then maximizes macro-F1 /
PRESENT recall / NONE recall / uncertain band width. No feasible pair →
`SETTLED_FAIL`. Gates are not loosened.

## Acceptance gates (unchanged)

```text
false_evidence_entry_rate_on_none <= 0.05
EVIDENCE_PRESENT recall >= 0.70
NO_EVIDENCE recall >= 0.90
```

No family metric participates in Stage-A acceptance.

## Label provenance

Sidecar `LABEL_PROVENANCE.jsonl` (does **not** rewrite
`EVIDENCE_SURFACE.jsonl` / dataset SHA). Orthogonal to source
`OBSERVED|INFERRED`. Forbidden final authorities include model prediction,
Jev, reserve results, unversioned heuristics.

Require `invalid_provenance_rows = 0` before authorization seals.

## Runner fail-closed latch

`scripts/spark/run_classification_v5_stage_a_train.py` refuses unless:

```text
train_authorized == true
dataset_sha256 == a81ca68a…
surface_readiness == PASS
resolved_config_sha256 matches authorized config
CURRENT_BEST == 9fba0f66…
reserve_consumed == false
```

Execute only with `HLX_V5_STAGE_A_EXECUTE_TRAIN=1`.

## Private artifacts

`hlx-private/classification-v5-stage-a-train-20260930/`:

- `AUTHORIZATION.json`
- `RESOLVED_TRAINING_CONFIG.json`
- `CLASS_WEIGHTS.json`
- `LABEL_PROVENANCE.jsonl` + `LABEL_PROVENANCE_STATS.json`
- `STAGE_A_TRAIN_CONTRACT.json`
- `SUMMARY.json`
- `ARTIFACT_HASHES.json`

## Hard prohibitions honored

No train in this pass. Dataset body unmodified. Readiness / acceptance gates
unmodified. Reserve unused. BEST unchanged. No family / focal / contrastive /
prototype / reserve-derived loss.

## Exact next action

```text
TRAIN_V5_STAGE_A_ONCE
```
