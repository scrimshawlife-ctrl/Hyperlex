# Classification v5 — Apply gold identifiability filter (V1R2)

```text
RULE = APPLY_GOLD_IDENTIFIABILITY_FILTER
FILTER_ID = HYPERLEX_V5_STAGE_A_GOLD_IDENTIFIABILITY_FILTER_V1
SURFACE = HYPERLEX_V5_STAGE_A_IDENTIFIABILITY_FILTERED_SURFACE_V1R2
DATASET_VERSION = V1R2
PARENT = V1R1 / 4095036e5af3ad7c…
V1R2_DATASET = 492ed36751c7fdc4…
V1R2_ANNOTATIONS = 95d5436555da33ef…
CONTRACT_RECEIPT = 4ce0e5faccef3772…
TRAIN_AUTHORIZED = false
AUTO_RELABEL = false
V1R1_MUTATED = false
STAGE_A_BEST = cd2829c1… UNCHANGED
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
receipt = e8e2ab7f6773717e…
NEXT_ACTION = AUTHORIZE_STAGE_A_IDENT_FILTERED_FACTORIZED_TRAIN
```

Membership filter only under `HYPERLEX_STAGE_A_GOLD_IDENTIFIABILITY_CONTRACT_V1`.
No train, auto-relabel, input expansion, Stage-B, reserve, or BEST moves.

## Counts

| Set | n |
|---|---:|
| parent V1R1 | 3585 |
| kept (V1R2) | 3120 |
| excluded | 465 |
| PRESENT | 1215 |
| NONE | 1851 |
| UNCERTAIN | 54 |
| relation_loss_eligible | 3066 |
| resolvability_loss_eligible | 3120 |
| SHORT_ATOM PRESENT kept | 11 |
| SHORT_ATOM NONE kept | 310 |

## Splits

| Split | n |
|---|---:|
| train | 2272 |
| validation | 848 |

## Viability

```text
relation +/- = 1215 / 1851
resolvability +/- = 3066 / 54
viability = REPAIRED_SURFACE_VIABLE
```

## Decision

```text
PRIMARY_REPAIR_APPLIED = FILTER_CONTEXT_DEPENDENT_GOLD
V1R2_CREATED = true
TRAIN_AUTHORIZED = false
NEXT_ACTION = AUTHORIZE_STAGE_A_IDENT_FILTERED_FACTORIZED_TRAIN
NEXT_ACTION_AUTHORIZED = false
```

Do **not** train until a fresh authorization binds this V1R2 surface.
