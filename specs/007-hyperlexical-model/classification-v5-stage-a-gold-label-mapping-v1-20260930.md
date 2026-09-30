# HYPERLEX_V5_STAGE_A_GOLD_LABEL_MAPPING_V1

Freeze date: 2026-09-30  
Module: `scripts/shadow/hyperlexical/classification_v5_stage_a_gold_label_mapping.py`

## Critical invariant

```text
Gold UNCERTAIN describes semantic uncertainty in the input evidence.
Inference-time UNCERTAIN describes the model's decision state.
They may share the output label, but inference uncertainty MUST NOT
be used retroactively to create or modify gold UNCERTAIN examples.
```

Gold labels are dataset-semantic. They MUST NOT be derived from model
probability, threshold outcome, retrieval/NN/prototype scores, reserve
behavior, or Jev.

## Canonical Stage-A gold labels

```text
0 = NO_EVIDENCE
1 = EVIDENCE_PRESENT
2 = UNCERTAIN
```

## Subtype → gold

| Evidence subtype | `required_evidence_present` | Stage-A gold |
|---|---|---|
| POSITIVE_EVIDENCE | `true` | `EVIDENCE_PRESENT` |
| ORDINARY_DOMAIN_NONE | `false` | `NO_EVIDENCE` |
| HARD_NONE | `false` | `NO_EVIDENCE` |
| NEAR_DOMAIN_NONE | `false` | `NO_EVIDENCE` |
| GENERIC_NONE | `false` | `NO_EVIDENCE` |
| LEXICAL_LOOKALIKE_NONE | `false` | `NO_EVIDENCE` |
| SHORT_ATOM_NONE | `false` | `NO_EVIDENCE` |
| AMBIGUOUS_EVIDENCE | `uncertain` | `UNCERTAIN` |

No subtype may map to more than one Stage-A label. Unknown subtype →
`LABEL_MAPPING_INVALID`.

## Family ambiguity

If evidence is clearly present but supports multiple families:

```text
Stage-A gold = EVIDENCE_PRESENT
```

Family ambiguity is Stage-C `AMBIGUOUS`, not Stage-A `UNCERTAIN`.

## Admission invariants

```text
subtype_gold_mismatch = 0
required_evidence_gold_mismatch = 0
positive_without_family_support = 0
uncertain_without_reason = 0
unknown_subtype = 0
```

Any violation → `LABEL_MAPPING_INVALID` and exclude the row from
train/validation.
