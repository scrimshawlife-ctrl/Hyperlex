# HYPERLEX_V5_STAGE_A_B_PIPELINE_V1

```text
PIPELINE_ID = HYPERLEX_V5_STAGE_A_B_PIPELINE_V1
V5_STAGE_A_STATE = CANONICAL_FROZEN
V5_STAGE_B_STATE = CANONICAL_FOR_V1R2_PIPELINE
V5_STAGE_A_B_PIPELINE_STATE = CANONICAL_FROZEN
STAGE_A_BEST = f2b00c5dfeb087288fc1686c901fbc8b52a8ba7a7b51cb83ff038656f93617fa
MODEL_WIDE_BEST = 9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6
STAGE_B_INDEX = 4febe96ea179597eb7792b376ed9eedbc9295a2fd8b5fa0eec969719f015c1f4
thresholds = relation 0.60 / resolvability 0.75
floors = score 0.83 / margin 0.01
flow = text -> Stage A -> stop|abstain|Stage B retrieval -> FAMILY|AMBIGUOUS|ABSTAIN
```

Active Stage-B is V1R2-aligned (`index_rebuilt=true`, `floors_retuned=true`).
Historical V1R9 index `3fd6c87a…` / floors 0.64/0.07 retained.
Parent pin: `STAGE_A_CANONICAL=HYPERLEX_V5_STAGE_A_CANONICAL_V1`.
Seal/package phase: `SEAL_AND_PACKAGE_HYPERLEX_V5_STAGE_A_B_V1R2_PIPELINE`.
