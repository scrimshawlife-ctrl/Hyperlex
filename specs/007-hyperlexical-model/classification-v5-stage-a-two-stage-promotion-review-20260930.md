# Classification v5 — Review two-stage Stage-A promotion

```text
RULE = REVIEW_V5_STAGE_A_TWO_STAGE_PROMOTION
EXPERIMENT_ID = HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-001
PROMOTION_REVIEW = VALID
PROMOTION_DECISION = PROMOTION_READY
SELECTED = cd2829c1…
SELECTED_EPOCH = 11
Gate1 = 0.75
Gate2 = 0.50
BEST = 9fba0f66… UNCHANGED
RESERVE = unused
TRAIN = false
NEXT_ACTION = PROMOTE_V5_STAGE_A_TWO_STAGE_SELECTED
```

Read-only review. No train, threshold change, reserve score, or BEST mutation.

## Settlement integrity — PASS

| Check | Result |
|---|---|
| Authorization receipt `c9b262de…` | PASS |
| Dataset SHA `8d4be830…` | PASS |
| Training-config SHA `0117faca…` | PASS |
| Class-weight artifact `5496015a…` | PASS |
| Architecture receipt `631427cc…` | PASS |
| Split witness `ecb88025…` | PASS |
| Selected checkpoint `cd2829c1…` | PASS |
| Selected epoch 11 | PASS |
| Threshold grid 100 pairs / `n_passing=4` | PASS |
| Frozen threshold rule (0.75 / 0.50) | PASS |
| Three acceptance gates | PASS |
| `SCIENTIFIC_RESULT=SETTLED_PASS` | PASS |
| Run receipt `9c358d2c…` | PASS |

## Cold-load / validation replay — PASS

Reconstruction: trunk → BEST encoder overlay (48 tensors) → SELECTED
last-2-layer overlay (12 tensors) → Gate1/Gate2 heads.

| Metric | Settled | Replay | Δ |
|---|---:|---:|---:|
| false_entry | 0.04233226837060703 | 0.04233226837060703 | 0 |
| PRESENT recall | 0.7048665620094191 | 0.7048665620094191 | 0 |
| NONE recall | 0.9089456869009584 | 0.9089456869009584 | 0 |
| UNCERTAIN recall | 0.6790123456790124 | 0.6790123456790124 | 0 |
| e2e macro-F1 | 0.7411485290305739 | 0.7411485290305739 | 0 |
| Gate1 / Gate2 | 0.75 / 0.50 | 0.75 / 0.50 | exact |

`replay_hash = fc601e69569594d55eb150ee9b467eb37ce0c1b3015e29d88d54aecb7eda6474`

## Architecture identity — PASS

SELECTED contains exactly: shared ModernBERT encoder overlay (layers 20/21),
Gate1 2-logit head, Gate2 2-logit head. No flat `evidence_head`. Earlier layers
remain structurally compatible via BEST parent overlay at load time.

## Canonical inference contract (frozen)

```text
p_possible = Gate1 P(POSSIBLE_EVIDENCE)
if p_possible < 0.75:
    NO_EVIDENCE
else:
    p_confirmed = Gate2 P(CONFIRMED_PRESENT)
    if p_confirmed >= 0.50:
        EVIDENCE_PRESENT
    else:
        UNCERTAIN
```

No runtime threshold search. Scalar three-state head forbidden.

## Residual known limitations

No frozen subgroup acceptance gates. Aggregate SETTLED_PASS stands.

| Subgroup diagnostic | Value | Status |
|---|---:|---|
| OBSERVED PRESENT recall | 0.657 | KNOWN_LIMITATION |
| OBSERVED NONE recall | 0.883 | KNOWN_LIMITATION |
| OBSERVED false-entry | 0.054 | KNOWN_LIMITATION |
| ATOM PRESENT recall | 0.696 | KNOWN_LIMITATION |

## Compatibility / migration

Semantic vocabulary unchanged: `NO_EVIDENCE` / `EVIDENCE_PRESENT` / `UNCERTAIN`.

| Surface | Impact |
|---|---|
| Stage-A canonical architecture | Changes to two-stage gates |
| Checkpoint loading | trunk + BEST + SELECTED overlay + heads |
| Runtime decision packet | `decide_two_stage(p_possible, p_confirmed)` |
| Downstream Stage-B entry | Semantic labels preserved |
| Family-retrieval | Adapter if consuming logits; labels OK |
| Schemas / API | Forward contract `stage_a_two_stage_forward.v1` |

Migration: flat `decide_evidence(P_PRESENT)` /
`DEPRECATED_FOR_V5_STAGE_A_CANONICAL_DECISION` → two-stage contract above.

## BEST semantics

Repository `BEST` (`9fba0f66…`) is the broader encoder seed, not the Stage-A
decision head. Recommendation: promote SELECTED to **`STAGE_A_BEST`** only.
Do not overwrite model-wide BEST.

## Reserve policy

Reserve unused; not scored in review. Existing Stage-A V5 policy does **not**
require a fresh reserve before internal canonical adoption or production
promotion for this component.

## Decision

```text
PROMOTION_DECISION = PROMOTION_READY
NEXT_ACTION = PROMOTE_V5_STAGE_A_TWO_STAGE_SELECTED
```

Promotion was **not** performed in this review. Subsequent component promotion:
see `classification-v5-stage-a-two-stage-promotion-20260930.md`
→ **`STAGE_A_PROMOTION=APPLIED`** / `STAGE_A_BEST=cd2829c1…`.

Receipt: `classification-v5-stage-a-two-stage-promotion-review-receipt-20260930.json`
(`7e09c67d…`).
