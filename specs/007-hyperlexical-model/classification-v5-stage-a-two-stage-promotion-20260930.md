# Classification v5 — Promote two-stage Stage-A selected

```text
RULE = PROMOTE_V5_STAGE_A_TWO_STAGE_SELECTED
EXPERIMENT_ID = HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-001
STAGE_A_PROMOTION = APPLIED
STAGE_A_BEST = cd2829c1…
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
BEST_MUTATED = false
RESERVE_CONSUMED = false
previous_STAGE_A_BEST = null
```

Component-scoped promotion only. No train, threshold change, V1R9 mutation,
weight rewrite, reserve score, or model-wide BEST overwrite.

## Preflight — PASS

| Check | Result |
|---|---|
| `PROMOTION_REVIEW=VALID` | PASS |
| `PROMOTION_DECISION=PROMOTION_READY` | PASS |
| Review receipt `7e09c67d…` | PASS |
| Validation replay `fc601e69…` | PASS |
| Selected `cd2829c1…` / epoch 11 | PASS |
| `SCIENTIFIC_RESULT=SETTLED_PASS` | PASS |
| Pre-mutation cold-load | PASS |

## STAGE_A_BEST pointer

| Field | Value |
|---|---|
| checkpoint_sha256 | `cd2829c1…` |
| architecture | `HYPERLEX_V5_STAGE_A_TWO_STAGE_DECISION_GRAPH_V1` |
| gate1_threshold | 0.75 |
| gate2_threshold | 0.50 |
| parent_encoder_best | `9fba0f66…` |
| forward schema | `stage_a_two_stage_forward.v1` |

On-host pointer: `~/.hyperlex/models/STAGE_A_BEST` →
`hyperlex-encoder-modernbert-base-seed-classification-v5-stage-a-two-stage-001`.
Model-wide `BEST` remains `select004` / `9fba0f66…`.

## Canonical load path

```text
ModernBERT trunk
→ model-wide BEST encoder overlay
→ STAGE_A_BEST adapted layers 20/21
→ gate1_head
→ gate2_head
```

Fail closed on parent BEST mismatch, overlay name/shape mismatch, missing
Gate1/Gate2 heads, or flat `evidence_head` as canonical.

## Canonical inference

```text
p_possible = Gate1 P(POSSIBLE_EVIDENCE)
if p_possible < 0.75 → NO_EVIDENCE
else if Gate2 P(CONFIRMED_PRESENT) ≥ 0.50 → EVIDENCE_PRESENT
else → UNCERTAIN
```

No runtime threshold search. No scalar `P(PRESENT)` fallback.

## Runtime adapter / Stage-B

| Stage-A label | Downstream |
|---|---|
| `NO_EVIDENCE` | STOP |
| `UNCERTAIN` | ABSTAIN (no family retrieval) |
| `EVIDENCE_PRESENT` | Stage-B permitted |

Semantic vocabulary unchanged. Callers need not understand Gate1/Gate2.

## Deprecated flat path

Status: `DEPRECATED_FOR_CANONICAL_STAGE_A`  
Allowed only: historical replay, scientific comparison, compatibility diagnostics.
Historical artifacts retained.

## Post-promotion replay — PASS

Exact parity with promotion-review replay hash `fc601e69…`:

| Metric | Value |
|---|---:|
| false_entry | 0.04233226837060703 |
| PRESENT recall | 0.7048665620094191 |
| NONE recall | 0.9089456869009584 |
| UNCERTAIN recall | 0.6790123456790124 |
| e2e macro-F1 | 0.7411485290305739 |
| Gate1 / Gate2 | 0.75 / 0.50 |

## Known limitations

| Diagnostic | Value | Status |
|---|---:|---|
| OBSERVED PRESENT recall | 0.657 | KNOWN_LIMITATION |
| OBSERVED NONE recall | 0.883 | KNOWN_LIMITATION |
| OBSERVED false-entry | 0.054 | KNOWN_LIMITATION |
| ATOM PRESENT recall | 0.696 | KNOWN_LIMITATION |

## Receipt

`classification-v5-stage-a-two-stage-promotion-receipt-20260930.json`  
`STAGE_A_PROMOTION_RECEIPT_SHA256 = d4c0cfd6…`

## Next action

```text
NEXT_ACTION = STOP_STAGE_A_ARCHITECTURE_WORK
```

Stage-A architecture work stops unless production evidence exposes a new
failure mode. Stage-B integration against this contract:
see `classification-v5-stage-b-20260930.md`
→ **`RESERVE_SEAL_AUTHORIZED`** / `AUTHORIZE_SEAL_NEW_V5_RESERVE_THEN_ONE_SHOT_SCORE`.
