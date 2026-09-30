# Classification v3 — Stage A train seal

```text
HYPERLEX_CLASSIFICATION_V3_STAGE_A_TRAIN_V1
lifecycle = RUNNING
primary_gate = PASS
false_evidence_entry_rate_on_none ≈ 0.0059 <= 0.05
BEST = UNCHANGED
v3_reserve = none
```

One authorized train on `HYPERLEX_V3_EVIDENCE_SURFACE_V1` (dataset `7339c044…`).  
Frozen validation thresholds: `none_threshold=0.05`, `present_threshold=0.55`.

Public receipt: `classification-v3-stage-a-receipt-20260930.json`.  
Private seal: `/home/morpheus/hlx-private/classification-v3-stage-a-20260930/`.  
Weights: `~/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-classification-v3-stage-a/`.

## Next action

```text
WIRE_STAGE_B_RETRIEVAL_ON_EVIDENCE_PRESENT_THEN_VALIDATE
```

Do not seal a fresh reserve until Stage B is wired and validation still passes the primary false-entry gate with family emission precision ≥ 0.80.
