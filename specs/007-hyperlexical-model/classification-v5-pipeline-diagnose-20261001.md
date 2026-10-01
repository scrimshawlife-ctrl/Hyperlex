# DIAGNOSE_V5_PIPELINE_BEFORE_PACKAGING

## Result

```text
PRIMARY_DIAGNOSIS = STAGE_A_V1R2_CANONICAL_ON_STAGE_B_V1R9_SURFACE
PIPELINE_EVAL_PASS = false
gating_pass = true
false_entry_on_v1r9 = 0.19489
family_emission_precision = 0.7608695652173914
PACKAGING_READY = false
PIPELINE_DIAGNOSIS_RECEIPT_SHA256 = f3e7cabe03de16f1158bb6c8e6e4a7f310bc6683a11c45f7f5907e29aff8a165
```

## Root causes

1. **Surface mismatch** — Stage-A canonical on V1R2 ident-filtered gold; Stage-B frozen index/eval surface is V1R9.
2. **Index encoder parent mismatch** — index embeddings sealed under superseded `cd2829c1…`; queries use `f2b00c5d…`. Index rebuild forbidden by freeze.

Entry gating (NONE/UNCERTAIN never enter Stage B) is intact. Do not claim full pipeline pass on V1R9. Do not score spent reserve. Do not Hub-publish.

## Next phase

```text
NEXT_ACTION = ALIGN_V5_STAGE_B_TO_V1R2_OR_SCOPED_CROSS_SURFACE_EVAL
```
