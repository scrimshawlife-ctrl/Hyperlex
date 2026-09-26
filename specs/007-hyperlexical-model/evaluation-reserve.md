# Evaluation reserve (GEN-0)

Text identity is `hyperlexical.holdout_guard.normalized_text_sha256`.
That is SHA-256 of `heldout_census.normalize_group_text`: NFKC, casefold, URL strip, non-alphanumeric to space, whitespace collapse. Empty normalized text still hashes. No second normalizer is an identity. `soft_ceiling.clean_surface` remains the unbind-clean slice predicate only.

Row ids are historical labels. One text identity may carry many row ids. Contamination, spending, abandonment, and reserve membership attach to the text hash.

## Exhaustion

On 2026-09-26 the live store (`01c1b38fd6e926962e47a520228e884ae7d99ea0ad6bbe188dc9980064254ac2`, 5005 rows) had **zero** rows eligible for a fresh holdout after split=test, the pinned morph78 export (`64b7d3dede25047cb6dd2e5b663f7fa72946ec82ac1a8816ae34622d1aaac430`, 9150 rows), spent v2, rc1 unbind rows, and the abandoned SELECT-001 / SELECT-002 holdouts. The 440 `split=test` rows are also training-consumed under the canonical hash, so dropping the split gate does not open a fresh classify set. Classify OBSERVED and classify non-none in that eligible universe are 0.

SELECT-001 is `CLOSED_AT_LAUNCH_GATE`. SELECT-002 is `EXECUTION_INVALID` (0 epochs, 0 gradient steps). Both holdouts are `UNSCORED_ABANDONED`: never scored, not reusable, not `SCORED_SPENT`. Manifest bytes stay as sealed. Do not reopen either experiment.

## Lifecycle

New text is routed **before** training exposure. Records are append-only. Flags that mean consumed, spent, or abandoned only turn on.

```text
NEW
 |
 +--> TRAIN_CANDIDATE
 |       |
 |       +--> TRAIN_CONSUMED
 |
 +--> EVAL_RESERVE
         |
         +--> EVAL_BOUND
                 |
                 +--> EVAL_SPENT
                 |
                 +--> EVAL_ABANDONED
```

`AVAILABLE` is catalogued text with none of those flags. It may still be routed to `TRAIN_CANDIDATE` or `EVAL_RESERVE`.

Forbidden without a governed generation reset:

- `EVAL_RESERVE` or `EVAL_BOUND` later entering training
- training-consumed text later used as unseen evaluation
- spent or abandoned text returning to the fresh reserve

A generation-reset **request** can be recorded. It does not clear flags and it does not create a new baseline. GEN-1 is not opened by this policy.

## Assignment

Policy id: `hyperlex.eval_reserve.v1`. Fixed before any candidate output is observed. Model scores, errors, and predictions are refused as admission inputs.

Within a batch, identities are ordered by `sha256(GEN-0 | batch_id | normalized_text_sha256)`. A new identity is `EVAL_RESERVE` when it still fills at least one open required slice. Otherwise it is `TRAIN_CANDIDATE`. Quotas are unique text identities, not raw rows. A second row id on an existing hash does not increase the evaluation sample size. A new hash that reuses an old row id stays a different identity and is reported as a collision.

Required slices, because checkpoint selection needs each of them:

- `classify` (classification accuracy)
- `classify_observed` (OBSERVED-label accuracy)
- `classify_non_none` (`classify_macro_f1_nonnone`)
- `unbind_clean` (unbind clean exact)

## Coverage classes

| Claim | Class |
| --- | --- |
| Canonical text hash is the contamination identity | CANONICAL_REQUIREMENT |
| Fresh evaluation text is disjoint from training, spent, and abandoned text | CANONICAL_REQUIREMENT |
| Each required slice is represented before SELECT-003 can be drafted | CANONICAL_REQUIREMENT |
| Statistical minimum n for those metrics | NOT_COMPUTABLE |
| v2 `DRAW_READY_MIN` 470 | HISTORICAL_PRECEDENT (unbind census target; PR #113 sets no v2 size) |
| Name-gate 2500 | CANONICAL_REQUIREMENT for the name gate, not for this holdout |
| rc1 classify_clean 444 / OBSERVED 72 / unbind_clean 306 | HISTORICAL_PRECEDENT (spent test) |
| SELECT-002 eligibility 606 classify / 287 OBSERVED / 604 non-none / 250 clean unbind | HISTORICAL_PRECEDENT and the PLANNING_TARGET |

The planning target restores that SELECT-002 shape. It is not a validity theorem. Gap versus a statistical minimum is `NOT_COMPUTABLE`.

## Admission

```sh
PYTHONPATH=scripts/shadow python -m hyperlexical.identity_ledger admit \
  --ledger /path/to/ledger --rows new.jsonl --batch-id BATCH --source acquire
```

A row is accepted only when its canonical hash is absent from `TRAIN_CONSUMED`, `EVAL_SPENT`, `EVAL_ABANDONED`, and the existing reserve. The command reports raw rows and unique canonical text identities. Reserve rows must not be used for training, checkpoint selection, hyperparameter tuning, candidate-specific error review, or repeated scoring. Aggregate census counts are allowed. When `HLX_EVAL_RESERVE_LEDGER` is set, the trainer refuses if a loaded training row is still `EVAL_RESERVE` or `EVAL_BOUND`.

## SELECT-003

Do not draft SELECT-003 until a new reserve exists, the four slices are represented, the reserve is text-disjoint from the pinned training export, the reserve is not spent or abandoned, and this policy stays sealed. The unresolved hypothesis, if a later authorization allows it, is still `HLX_SELECT_METRIC`: `unbind_exact` versus `classify_macro_f1_nonnone`. Authorization is a separate act. Meeting a planning target does not grant it.

## GEN-0 and GEN-1

GEN-0 keeps `seed-morph78` and the pinned 9150-row export as the training baseline. New material is evaluation-only until the reserve slices are filled. Overflow may become `TRAIN_CANDIDATE` and must not be pulled back into the reserve.

GEN-0 becomes impractical only if, after a real acquisition attempt:

- new classify evidence cannot represent OBSERVED and non-none together
- new text keeps colliding with the pinned export or with spent/abandoned hashes
- accepted training candidates grow while the reserve slices stay empty
- the reserve cannot hold the four slices at once
- the historical baseline is no longer the system under test

Convenience is not one of those conditions. This document does not create GEN-1.

## Ledger

`scripts/shadow/hyperlexical/build_identity_ledger.py` catalogues receipt-backed artifacts. It does not infer lifecycle from filenames. The populated ledger stays on the host store, not in git, and does not contain raw text.

## Acquisition batch HLX-EVAL-ACQ-2026-09-26-001

Screened local rights-cleared and operator-labeled corpora. The ledger was not mutated. Decision `REJECT_BATCH`. The reserve stays empty.

- 2026 backfill atoms: 67/67 unique hashes already `TRAIN_CONSUMED`.
- Harvest multiword file: 890/890 unique hashes already `TRAIN_CONSUMED`.
- Civilian seed: 17 novel identities, all lineage `ai-native`. A registry export marked `OBSERVED` is not an operator settlement, so those rows were held. Class imbalance is severe. No balance threshold is declared.
- 2026-09-16 structure gold: the authorized train rows are already consumed. Four novel leftovers carry model predictions and were excluded.
- Agent-memetics seeds: rights are unresolved and task labels are absent.

New `OBSERVED` coverage is `NOT_COMPUTABLE` until an operator harvest settlement exists. This record does not settle phrases. SELECT-003 stays undrafted. GEN-1 was not created. In-repo settled gold is exhausted. That alone does not reset GEN-0.

