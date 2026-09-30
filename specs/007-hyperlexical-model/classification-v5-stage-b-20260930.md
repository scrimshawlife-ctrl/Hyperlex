# Classification v5 — Stage-B integration behind STAGE_A_BEST

```text
RULE = HYPERLEX_V5_STAGE_B_INTEGRATION_V1 / WIRE_V5_STAGE_B_RETRIEVAL_ON_STAGE_A_BEST
EXPERIMENT_ID = HLX-CLASSIFICATION-V5-STAGE-B-001
STAGE_A_BEST = cd2829c1… (frozen)
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
DATASET = V1R9 / 8d4be830…
primary_gate = PASS (false_entry = 0.04233226837060703)
secondary_gate = PASS (family emission precision ≈ 0.817)
authorization = RESERVE_SEAL_AUTHORIZED
v5_reserve = not created
BEST_MUTATED = false
RESERVE_CONSUMED = false
```

Family retrieval executes only when promoted Stage-A returns `EVIDENCE_PRESENT`.
`NO_EVIDENCE` → STOP / NONE. `UNCERTAIN` → ABSTAIN (never enters retrieval).

## Frozen Stage-A

| Field | Value |
|---|---|
| Architecture | `HYPERLEX_V5_STAGE_A_TWO_STAGE_DECISION_GRAPH_V1` |
| Gate1 / Gate2 | 0.75 / 0.50 |
| Load path | trunk → BEST → STAGE_A_BEST layers 20/21 → gate heads |
| Parent promotion | `d4c0cfd6…` |

## Index

Built from V1R9 train `POSITIVE_EVIDENCE` (603 rows; 17 surface families;
`ai-native` absent on this surface). Encoder embeddings from the promoted
Stage-A stack.

`index_sha256 = 3fd6c87a5825f3f2a25a81f1a769a77aa69e03ddca5b370f9247672d93aaee21`

## Calibrated Stage-B floors (validation)

| Floor | Value |
|---|---:|
| minimum_family_score | 0.64 |
| minimum_top1_top2_margin | 0.07 |

## Validation metrics

| Metric | Value | Gate |
|---|---:|---|
| false_entry on NONE | 0.04233226837060703 | ≤0.05 PASS |
| family emission precision | 0.8172043010752689 | ≥0.80 PASS |
| family emission coverage | 0.14599686028257458 | — |
| selective accuracy | 0.8771676300578035 | — |

## Receipt

`classification-v5-stage-b-validation-receipt-20260930.json`  
(`51323ff4…`)

Private seal: `/home/morpheus/hlx-private/classification-v5-stage-b-20260930/`.

## Next action

```text
NEXT_ACTION = AUTHORIZE_SEAL_NEW_V5_RESERVE_THEN_ONE_SHOT_SCORE
```

Do not score until a fresh v5 reserve is explicitly authorized and sealed.
Prior spent reserves remain permanently excluded. Do not mutate BEST or
STAGE_A_BEST.
