# Classification v5 — Reproduce ident-filtered factorized train once

```text
RULE = REPRODUCE_IDENT_FILTERED_FACTORIZED_TRAIN_ONCE
EXPERIMENT = HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-REPRO-001
PARENT_EXPERIMENT = HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-001
REPRODUCTION_REASON = SELECTED_FACTORIZED_HEADS_NOT_SERIALIZED
SCIENTIFIC_RESULT = SETTLED_PASS
REPRODUCTION_CLASSIFICATION = SCIENTIFICALLY_EQUIVALENT_REPRODUCTION
SELECTED_COMPLETE_CHECKPOINT = f2b00c5d…
FINAL_COMPLETE_CHECKPOINT = b6b9ddfc…
selected_epoch = 11
selected_thresholds = relation 0.60 / resolvability 0.75
selection_score = 0.9673
factorized_heads_cold_loadable = true
RUN_RECEIPT = 8b8585a8…
STAGE_A_BEST = cd2829c1… UNCHANGED
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
NEXT_ACTION = RETRY_PROMOTE_STAGE_A_IDENT_FILTERED_FACTORIZED_CANDIDATE
```

Single authorized reproduction train under frozen V1R2 scientific inputs.
Serializer fix retained factorized heads (`n_keys=16` including
`relation_head` / `resolvability_head` weight+bias). BEST pointers untouched.
Spent reserve unused.

## Acceptance gates

| Gate | Value | Limit | Pass |
|---|---:|---:|---|
| false_entry | 0.03357 | ≤ 0.05 | yes |
| PRESENT recall | 0.9513 | ≥ 0.70 | yes |
| NONE recall | 0.9647 | ≥ 0.90 | yes |

## Reproduction parity vs original SETTLED_PASS

| Metric | Original | Reproduction | Δ |
|---|---:|---:|---:|
| false_entry | 0.03357 | 0.03357 | 0 |
| PRESENT recall | 0.9513 | 0.9513 | 0 |
| NONE recall | 0.9647 | 0.9647 | 0 |
| SHORT_ATOM NONE relation FPR | 0.013 | 0.01316 | +0.00016 |
| selected epoch | 11 | 11 | 0 |
| thresholds | 0.60 / 0.75 | 0.60 / 0.75 | same |

Identifiability witness preserved:

```text
prior unfiltered SHORT_ATOM NONE relation FPR = 0.539
original ident-filtered = 0.013
reproduction = 0.01316
```

Classification is `SCIENTIFICALLY_EQUIVALENT_REPRODUCTION` (exact gate metrics
and selection; SHORT_ATOM FPR within rounding of the sealed 0.013 witness).
Not claimed as byte-identical `EXACT_REPRODUCTION`.

Limitations unchanged:

```text
SHORT_ATOM_POSITIVE_GENERALIZATION = LOW_SUPPORT
DOMAIN_IRRELEVANT_GENERALIZATION = NOT_ESTABLISHED
```

## Checkpoint packaging

Both selected and final complete checkpoints are independently cold-loadable
and include factorized heads + manifests. Encoder-only packaging defect is
absent.

## Exact next action

```text
RETRY_PROMOTE_STAGE_A_IDENT_FILTERED_FACTORIZED_CANDIDATE
```

Promote against `SELECTED_COMPLETE_CHECKPOINT = f2b00c5d…` (not the historical
incomplete `8b2de447…`).
