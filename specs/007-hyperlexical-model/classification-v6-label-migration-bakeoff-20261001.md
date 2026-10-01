# REBUILD_V6_LABELS_AND_RUN_ARCHITECTURE_BAKEOFF

```text
BAKEOFF_STATE = V6_BAKEOFF_NO_ADVANCE
NEXT_ACTION = CONTINUE_V6_ARCHITECTURE_BAKEOFF
RECEIPT = b936b49bbf0e3925a03f2c1bb6eb46bf7458c7a2f1e215f83cc6536266d2d453
selected = None
advance = False
GENERALIZATION_GAP_ACCEPTABLE = True
ABS_REP_FLOOR_OK = False
HIERARCHY_OK = True
best_rep_macro_f1 = 0.023839
best_hierarchy_violation_rate_rep = 0.000000
sample_n = 319
mean_set_jaccard = 0.9686520376175548
```

Amended three-level multi-label agreement + boundary top-up, deterministic
label migration, tracks A/B/C under MODEL_WIDE_BEST control. QUAL sealed.

Selection repair: prior advance was invalid — `0.0 or 1` coerced zero
hierarchy violations to 1.0, and absolute REP macro-F1 (~0.02) was below the
0.20 floor. Correct state is **V6_BAKEOFF_NO_ADVANCE**.
