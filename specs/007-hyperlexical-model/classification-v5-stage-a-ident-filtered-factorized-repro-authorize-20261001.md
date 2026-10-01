# Classification v5 — Authorize ident-filtered factorized reproduction train

```text
RULE = AUTHORIZE_REPRODUCE_IDENT_FILTERED_FACTORIZED_TRAIN
EXPERIMENT = HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-REPRO-001
PARENT_EXPERIMENT = HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-001
REPRODUCTION_REASON = SELECTED_FACTORIZED_HEADS_NOT_SERIALIZED
TRAIN_AUTHORIZED = true
TRAINING_STATUS = AUTHORIZED_NOT_STARTED
TRAINING_RUN_LIMIT = 1
SCIENTIFIC_RESULT = NOT_COMPUTABLE
SCIENTIFIC_CONFIG_PARITY = PASS
CLASS_WEIGHT_ARTIFACT = 13e8d0ca… REUSED (not recomputed)
ORIGINAL_TRAINING_CONFIG = e252f1ba…
REPRODUCTION_TRAINING_CONFIG = 731c0b26…
receipt = 09f3d456961aaa9027ff35ac653f3d6aeee627ceee1eb705fcd83dc9b9c3205b
STAGE_A_BEST = cd2829c1… UNCHANGED
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
NEXT_ACTION = REPRODUCE_IDENT_FILTERED_FACTORIZED_TRAIN_ONCE
```

Authorization only. No train. V1R2 / annotations / exclusion / thresholds /
architecture / Stage B / BEST pointers unchanged. Spent reserve remains `SPENT`
and was not scored.

## Why this experiment exists

The original run is scientifically `SETTLED_PASS` (receipt `4a7d565c…`, epoch 11).
Promotion failed because serialization dropped `relation_head` /
`resolvability_head`. Repair scanned retained artifacts (`hit_count=0`) and
sealed `REPAIR_NOT_POSSIBLE_WITHOUT_RETRAIN` (`6b041947…`).

This is a **reproduction**, not a new hypothesis. The only intended
implementation difference is the already-landed serializer fix (`9edf8fc`).

## Scientific invariance

| Pin | Value |
|---|---|
| dataset | `492ed367…` V1R2 |
| annotations | `95d54365…` |
| exclusion | `661c9edb…` |
| objective | `HYPERLEX_V5_STAGE_A_FACTORIZED_RELATION_OBJECTIVE_V1` |
| init | `FRESH_RETRAIN_FROM_MODEL_WIDE_BEST` `9fba0f66…` |
| architecture | shared ModernBERT + CLS + relation_head(2) + resolvability_head(2); last 2 layers |
| loss | `L_relation + 1.0 * L_resolvability` |
| optimizer | AdamW lr `2e-5` wd `0.01` batch 8 accum 1 |
| schedule | max 12 / min 4 / patience 4 / warmup 0.05 / clip 1.0 |
| seed | 42 |
| max_len | 64 |
| sampling | deterministic full-pass; no replacement; no over/under sampling |

## Split identity (live V1R2 verified)

| Set | n | SHA |
|---|---:|---|
| TRAIN_ROWS / TRAIN_SPLIT | 2272 | `d0eb1f10…` |
| VALIDATION_ROWS / VALIDATION_SPLIT | 848 | `52f234ce…` |
| TRAIN_IDENTITY | 2272 | `69ef5c78…` |
| VALIDATION_IDENTITY | 848 | `03add594…` |
| RELATION_ELIGIBLE_TRAIN | 2233 | `2ac99867…` |
| RELATION_MASKED_TRAIN | 39 | `77b43171…` |

## Class weights (reused literals)

```text
relation:
  NO_EVIDENCE_RELATION = 0.8985774732156429
  EVIDENCE_RELATION_PRESENT = 1.1014225267843571
resolvability:
  UNRESOLVABLE = 1.7030222347950057
  RESOLVABLE = 0.5
```

## RNG contract

Established from the original runner, not redefined:

```text
torch.manual_seed(42)
→ load tokenizer/trunk
→ overlay MODEL_WIDE_BEST
→ freeze last 2
→ Linear() relation then resolvability
→ Xavier relation weight / zero bias
→ Xavier resolvability weight / zero bias
```

Gaps recorded (not silently closed): no CUDA/numpy/cudnn seed in the original
runner; tokenizer/encoder construction sits between `manual_seed` and Xavier.
Implication: `ORDER_ESTABLISHED_NOT_BYTE_GUARANTEED`.

## Serialization / save policy

`require_factorized_heads_in_flat = true` on every candidate save.
Encoder-only factorized checkpoints are invalid.
Retain independently cold-loadable `SELECTED_COMPLETE_CHECKPOINT` and
`FINAL_COMPLETE_CHECKPOINT`. Each saved checkpoint must carry a head/encoder
tensor manifest.

Serialization regression tests: PASS.

## Selection / gates (unchanged)

```text
selection_score = 0.50 * relation_macro_F1 + 0.50 * resolvability_macro_F1
tie-break: lower relation FPR → higher PRESENT recall → higher UNRESOLVABLE recall → earlier epoch
threshold grid: 10 × 10 = 100 pairs; do not force 0.60 / 0.75
gates: false_entry ≤ 0.05; PRESENT recall ≥ 0.70; NONE recall ≥ 0.90
```

Reproduction classification (`EXACT` / `NUMERICALLY_EQUIVALENT` /
`SCIENTIFICALLY_EQUIVALENT` / `DIVERGED`) is deferred until the run.
Limitations remain `SHORT_ATOM_POSITIVE_GENERALIZATION=LOW_SUPPORT` and
`DOMAIN_IRRELEVANT_GENERALIZATION=NOT_ESTABLISHED`.

Do **not** train until `REPRODUCE_IDENT_FILTERED_FACTORIZED_TRAIN_ONCE` is
explicitly executed.
