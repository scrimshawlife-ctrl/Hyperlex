# Classification v5 — Gold Identifiability Contract V1

```text
RULE = REVISE_GOLD_IDENTIFIABILITY_CONTRACT
CONTRACT = HYPERLEX_STAGE_A_GOLD_IDENTIFIABILITY_CONTRACT_V1
STATE = FROZEN_SPEC
TRAIN_AUTHORIZED = false
DATASET_MUTATED = false
MODEL_INPUT = ['text']
PRIMARY_REPAIR = FILTER_CONTEXT_DEPENDENT_GOLD
DATASET_CONSEQUENCE = ANNOTATION_FILTER_ONLY
NEXT_ACTION = APPLY_GOLD_IDENTIFIABILITY_FILTER
NEW_DATASET_VERSION_REQUIRED = True
STAGE_A_BEST = cd2829c1… UNCHANGED
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
receipt = 4ce0e5faccef3772…
```

Spec + read-only V1R1 audit. No train, auto-relabel, V1R2, input enrichment, Stage-B, reserve, or BEST moves.

## Canonical principle

> A text-only classifier may not be trained or evaluated against a semantic distinction that requires hidden metadata, pair context, source provenance, dictionary sense, or annotation-side information unavailable at inference.

## Identifiability counts (V1R1 n=3585)

| State | n |
|---|---:|
| TEXT_IDENTIFIABLE | 3066 |
| CONTEXT_REQUIRED | 145 |
| INSUFFICIENT_TEXT | 54 |
| INVALID_GOLD_FOR_TEXT_ONLY_MODEL | 320 |

## SHORT_ATOM dispositions

| Disposition | n |
|---|---:|
| SELF_CONTAINED_RELATION | 13 |
| LEXEME_ONLY | 308 |
| CONTEXT_DEPENDENT_RELATION | 315 |
| SEMANTICALLY_UNDERDETERMINED | 0 |

## PRESENT identifiability

| Slice | total | TEXT_IDENTIFIABLE | INVALID |
|---|---:|---:|---:|
| all PRESENT | 1535 | 1215 | 320 |
| SHORT_ATOM PRESENT | 326 | 11 | 315 |
| PROSE PRESENT | 901 | 896 | 5 |
| DEFINITION_STYLE PRESENT | 308 | 308 | 0 |

## Admissibility / dispositions

```text
relation_train_admissible = 3066
resolvability_train_admissible = 3120
e2e_eval_admissible = 3120
EXCLUDE_FROM_TEXT_ONLY_STAGE_A = 465
REQUIRES_HUMAN_RESETTLEMENT = 0
KEEP_GOLD = 3066
KEEP_FOR_RESOLVABILITY_ONLY = 54
```

## Minimum viable repaired surface (planning witness)

```text
relation_train_eligible = 3066
  PRESENT = 1215  NONE = 1851
  SHORT_ATOM PRESENT = 11
  SHORT_ATOM NONE = 310
resolvability_train_eligible = 3120
e2e_evaluation_eligible = 3120
viability = REPAIRED_SURFACE_VIABLE
```

## Decision

```text
PRIMARY_REPAIR = FILTER_CONTEXT_DEPENDENT_GOLD
DATASET_CONSEQUENCE = ANNOTATION_FILTER_ONLY
REPAIR_SCOPE = FILTER_ONLY
NEW_DATASET_VERSION_REQUIRED = True
architecture_change_justified = false
input_contract_expansion_justified = false
NEXT_ACTION = APPLY_GOLD_IDENTIFIABILITY_FILTER
NEXT_ACTION_AUTHORIZED = false
```

Proposed future gates: relation training 100% TEXT_IDENTIFIABLE; context-required definitive gold = 0.

Do **not** apply the repair in this pass.
