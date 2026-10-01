# Classification v5 — promotion reserve seal + one-shot score

```text
RESERVE_ID = HYPERLEX_V5_PROMOTION_RESERVE_001
RULE = HYPERLEX_V5_PROMOTION_RESERVE_SEAL_SCORE_V1
STAGE_A_BEST = cd2829c1… UNCHANGED
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
Stage-B index = 3fd6c87a… UNCHANGED
floors = score 0.64 / margin 0.07 UNCHANGED
n = 250
settlement = RESERVE_FAIL
evaluation_spent = true
BEST_MUTATED = false
STAGE_A_BEST_MUTATED = false
```

Fresh disjoint promotion reserve sealed, then scored exactly once under the
frozen Stage-A two-stage + Stage-B retrieval pipeline. No training, no index
rebuild, no threshold retune, no automatic production promotion.

## Phase A — seal

| Field | Value |
|---|---|
| total | 250 |
| NO_EVIDENCE | 61 |
| EVIDENCE_PRESENT | 159 |
| UNCERTAIN | 30 |
| distinct PRESENT families | 15 |
| max family share of PRESENT | 0.1698 |
| OBSERVED overall / NONE / PRESENT | 0.824 / 0.672 / 1.000 |
| disjointness | PASS (0 blocked hits) |

NONE subtypes: ORDINARY 20, HARD 12, NEAR 12, GENERIC 8, SHORT_ATOM 8,
LOOKALIKE 1.

Hashes:

| Artifact | sha256 |
|---|---|
| rows | `0b71fcbf…8032d711` |
| identity list | `bc87c62d…5498a82` |
| manifest | `6d475119…dc87e1a1` |
| seal | `21903bea…ceb1e360` |

Private seal: `/home/morpheus/hlx-private/classification-v5-reserve-20260930/`.

## Phase B — one-shot score

Frozen runtime: Gate1=`0.75`, Gate2=`0.50`, Stage-B floors `0.64` / `0.07`,
index `3fd6c87a…`.

| Gate | Metric | Value | Limit | Result |
|---|---|---:|---:|---|
| Primary | false_evidence_entry_rate_on_none | 0.0984 | ≤0.05 | FAIL |
| Secondary | family_emission_precision | 0.6667 | ≥0.80 | FAIL |

| Diagnostic | Value |
|---|---:|
| PRESENT / NONE / UNCERTAIN recall | 0.371 / 0.574 / 0.600 |
| FAMILY / ABSTAIN / AMBIGUOUS / NONE | 15 / 123 / 40 / 72 |
| family emission coverage / recall | 0.094 / 0.063 |
| family top1 / top2 accuracy | 0.151 / 0.208 |
| wrong emissions | 5 |

Wrong-emission breakdown: `STAGE_A_FALSE_ENTRY=1`, `STAGE_B_WRONG_FAMILY=1`,
`STAGE_A_AND_B_COMPOUND=3`.

## Settlement

```text
RESERVE_FAIL
```

Reserve identities marked `evaluation_spent=true` (ledger marks applied where
present). Do not retune against this reserve. Do not promote.

## Receipt

`classification-v5-promotion-reserve-receipt-20260930.json`  
(`2e083b9e…`)

## Next action

```text
NEW_STAGE_A_TRAINING_SURFACE — diagnosis STAGE_A_GENERALIZATION_FAILURE
(see classification-v5-reserve-fail-diagnose-20261001.md); preserve spent
reserve; do not retune thresholds; do not train on reserve mistakes.
```
