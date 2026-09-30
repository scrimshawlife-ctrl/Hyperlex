# Classification v3 — Stage B validation seal

```text
HYPERLEX_CLASSIFICATION_V3_STAGE_B_RETRIEVAL_V1
retrieval only on Stage A EVIDENCE_PRESENT
primary_gate = PASS (false_entry ≈ 0.0059)
secondary_gate = PASS (family emission precision ≈ 0.815)
authorization = RESERVE_SEAL_AUTHORIZED
v3_reserve = not created
BEST = UNCHANGED
```

Frozen Stage A thresholds: `none=0.05`, `present=0.55`.  
Calibrated Stage B floors: `minimum_family_score=0.96`, `minimum_top1_top2_margin=0.01`.

Index built from evidence-surface train `POSITIVE_EVIDENCE` (18 families) using the Stage A encoder. Spent v2 reserve unused.

Public receipt: `classification-v3-stage-b-receipt-20260930.json`.  
Private seal: `/home/morpheus/hlx-private/classification-v3-stage-b-20260930/`.

## Next action

```text
AUTHORIZE_SEAL_NEW_V3_RESERVE_THEN_ONE_SHOT_SCORE
```

Do not score until a fresh v3 reserve is explicitly authorized and sealed. The spent v2 reserve remains permanently excluded.
