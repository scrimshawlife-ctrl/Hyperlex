# REDESIGN_V6_REPRESENTATIVE_VALIDATION_AND_DATA_DIVERSITY

```text
REPRESENTATIVENESS_REPAIRED = True
REMAINING_MODEL_FAILURE = NONE_REJECTION_FAILURE
NEXT_ACTION = HARDEN_V6_NONE_REJECTION_UNDER_FROZEN_ENCODER
REP_V2 n = 1416 zero_label_share = 0.620
REP_V2 system macro-F1 = 0.2203
REP_V2 FUNCTION macro-F1 = 0.2227
REP_V2 zero-label FP rate = 0.788
old usable REP ≈ 0.432
QUAL-002 system macro-F1 = 0.1885
RECEIPT = 7e3b6f01a223c4f612866314f799dfc98713fb74c616880d1d70748f7bb3e1cf
```

Removed `usable()` positive-only filtering. REP_V2 includes NONE/NO_EVIDENCE
mass and dual-discovered co-labels. Hardened package `a88275837b34…`
replayed unchanged. QUAL-002 rows not used for optimization.
