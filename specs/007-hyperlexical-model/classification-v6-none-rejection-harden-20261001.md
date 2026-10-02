# HARDEN_V6_NONE_REJECTION_UNDER_FROZEN_ENCODER

```text
DISPOSITION = V6_NONE_REJECTION_ADVANCE
NEXT_ACTION = HARDEN_V6_FULL_OPERATING_PIPELINE_AND_PREPARE_NEW_QUALIFICATION
selected_mechanism = LEARNED_ANY_EVIDENCE_GATE
REP_V2 system macro-F1 = 0.3698
REP_V2 positive-only = 0.4158
REP_V2 zero-label FP = 0.088 (was 0.788)
REP_V2 zero exact reject = 0.912
REP_V2 mean pred on zero = 0.145
false_reject_positive = 0.416
encoder_immutable = true
RECEIPT = 246fe8421a9cb5768bc4a6e88afc9e93420d9243cf20d97b2ccce35f72f71b05
```

Two-stage gate: frozen embedding → ANY_LABEL/ZERO_LABEL gate →
axis heads → hierarchy. Surfaces TRAIN/DEV/REP V2 frozen. QUAL-002 unused.
