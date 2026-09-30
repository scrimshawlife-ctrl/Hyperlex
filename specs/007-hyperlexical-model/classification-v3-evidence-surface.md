# Classification v3 — evidence surface seal

```text
HYPERLEX_V3_EVIDENCE_SURFACE_V1 = READY
HYPERLEX_CLASSIFICATION_V3_EVIDENCE_GATE = READY
train = false
v3_reserve = none
BEST = UNCHANGED
```

Built from admissible unspent hub train rows (`civilian.v0.7.hub.jsonl`). Spent v2 classify reserve identities permanently excluded. No Stage A training in this pass.

Public receipt: `classification-v3-evidence-surface-receipt-20260930.json`.  
Private seal: `/home/morpheus/hlx-private/classification-v3-evidence-surface-20260930/`.

## Next action

```text
TRAIN_STAGE_A_ONCE_AGAINST_PREREGISTERED_FALSE_ENTRY_GATE
```

Do not create or score a fresh reserve until validation passes the frozen false-entry gate.
