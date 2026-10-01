# Classification v5 — Stage-A semantic decomposition

```text
RULE = STAGE_A_SEMANTIC_DECOMPOSITION
EXPERIMENT = HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-GENERALIZATION-001
PRIMARY_DIAGNOSIS = GATE1_SEMANTIC_TARGET_MISMATCH
PRIMARY_DECOMPOSITION = RELATION_ONLY_DECOMPOSITION
MINIMUM_NEW_GOLD = NO_NEW_GOLD_REQUIRED
DATASET_CONSEQUENCE = ANNOTATION_ONLY_CHANGE
NEXT_ACTION = SPEC_STAGE_A_FACTORIZED_OBJECTIVE
NEXT_ACTION_AUTHORIZED = false
STAGE_A_BEST = cd2829c1… UNCHANGED
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
V1R1 = 4095036e… UNCHANGED
V1R2 = NOT_CREATED
TRAIN = false
RESERVE = SPENT / unused
diagnosis receipt = c6ae58c7…
decomposition receipt = 93202898…
```

Spec and evidence audit only. No train, V1R2, relabel, threshold change,
Stage-B mutation, spent-reserve use, or BEST moves.

## 1. Frozen semantic defect

```text
NO_EVIDENCE vs POSSIBLE_EVIDENCE
```

currently conflates domain relevance, lexical family cues, assertion presence,
relation presence, evidence sufficiency, and semantic uncertainty. This is
`GATE1_SEMANTIC_TARGET_MISMATCH`, not insufficient dataset size.

## 2. Canonical semantic axes

| Axis | Question | Values |
|---|---|---|
| DOMAIN_RELEVANCE | Does the text concern a tracked Hyperlex domain/family? | DOMAIN_IRRELEVANT / DOMAIN_RELEVANT / DOMAIN_RELEVANCE_UNCERTAIN |
| EVIDENCE_RELATION | Does the text assert/instantiate the required evidence relation/core? | NO_EVIDENCE_RELATION / EVIDENCE_RELATION_PRESENT / EVIDENCE_RELATION_UNCERTAIN |
| SEMANTIC_RESOLVABILITY | Is the evidence judgment semantically resolvable from the text? | RESOLVABLE / UNRESOLVABLE |

Mandatory distinctions:

```text
DOMAIN_RELEVANT ≠ EVIDENCE_PRESENT
LEXICAL_CUE ≠ EVIDENCE_RELATION
MODEL_UNCERTAINTY ≠ SEMANTIC_UNCERTAINTY
```

## 3. Deterministic final decision logic

```text
if semantic_resolvable == 0:
    UNCERTAIN
elif domain_relevant == 0:
    NO_EVIDENCE
elif evidence_relation_present == 0:
    NO_EVIDENCE
elif domain_relevant == 1 and evidence_relation_present == 1:
    EVIDENCE_PRESENT
else:
    UNCERTAIN
```

Final Stage-A labels remain `NO_EVIDENCE` / `EVIDENCE_PRESENT` / `UNCERTAIN`.
Neural architecture is unspecified in this pass.

## 4. Existing-label backward mapping

| Final gold | Unique reverse map? | Implies |
|---|---|---|
| EVIDENCE_PRESENT | yes | domain=1, relation=1, resolvable=1 |
| NO_EVIDENCE | **no** | resolvable=1, relation=0; domain 0 vs 1+no-relation ambiguous from final alone |
| UNCERTAIN | **no** | resolvable=0; which axis is unresolved is not unique |

Subtype metadata is required to recover domain relevance for NONE rows.

## 5. Subtype recoverability (V1R1)

| Subtype | n | Status | domain | relation | resolvable |
|---|---:|---|---:|---:|---:|
| POSITIVE_EVIDENCE | 1535 | DETERMINISTIC | 1 | 1 | 1 |
| ORDINARY_DOMAIN_NONE | 637 | DETERMINISTIC | 1 | 0 | 1 |
| LEXICAL_LOOKALIKE_NONE | 744 | DETERMINISTIC | 1 | 0 | 1 |
| SHORT_ATOM_NONE | 284 | DETERMINISTIC | 1 | 0 | 1 |
| NEAR_DOMAIN_NONE | 145 | DETERMINISTIC | 1 | 0 | 1 |
| HARD_NONE | 41 | DETERMINISTIC | 1 | 0 | 1 |
| AMBIGUOUS_EVIDENCE | 199 | PARTIALLY_DETERMINISTIC | ? | ? | 0 |
| GENERIC_NONE | 0 | NOT_DETERMINABLE | ? | 0 | 1 |

All present V1R1 NONE mass is domain-adjacent (`DOMAIN_RELEVANT_NO_RELATION`).
`GENERIC_NONE` / true `DOMAIN_IRRELEVANT` mass is absent.

## 6. Row-level annotation recoverability

| Axis | DIRECTLY_SUPPORTED | RULE_DERIVABLE | REQUIRES_NEW_HUMAN_SETTLEMENT |
|---|---:|---:|---:|
| domain_relevant | 1535 | 1851 | 199 |
| evidence_relation_present | 1535 | 1851 | 199 |
| semantic_resolvable | 1734 | 1851 | 0 |

Human settlement on the 199 UNCERTAIN rows would split *which* axis is
unresolved; it is **not** required to unblock the diagnosed SHORT_ATOM mismatch.

## 7. Evidence-relation definition

`EVIDENCE_RELATION_PRESENT` requires more than domain membership or lexeme
occurrence. Sufficient forms: explicit predicate/relation, asserted action/state,
clear semantic proposition, or context establishing the required evidence core.
Insufficient forms: isolated category label, dictionary headword, topic mention,
family-associated token alone, entity/name alone, unasserted list item.
Source-independent.

## 8. Short-atom semantic rule

1–4 token inputs are not banned and are not auto-NONE.

- `EVIDENCE_PRESENT` only when the short span still asserts/instantiates the
  required relation/core.
- Otherwise a domain cue is `DOMAIN_RELEVANT` + `NO_EVIDENCE_RELATION`
  (the diagnosed SHORT_ATOM NONE failure mode).

## 9. Relation-taxonomy recommendation

Prefer **binary** `evidence_relation_present`
(`NO_EVIDENCE_RELATION` / `EVIDENCE_RELATION_PRESENT` /
`EVIDENCE_RELATION_UNCERTAIN`). Finer asserted-state/action taxonomy deferred.

## 10. NONE semantic-reason recommendation

Do **not** mutate the current subtype ontology in this pass. Keep
surface/hardness subtypes; optionally add a parallel `semantic_reason` later
(`DOMAIN_IRRELEVANT` | `DOMAIN_RELEVANT_NO_RELATION` | `NEGATED_RELATION` |
`NONASSERTED_REFERENCE` | `INSUFFICIENT_CONTEXT`). Current V1R1 NONE mass
interprets as `DOMAIN_RELEVANT_NO_RELATION`.

## 11. UNCERTAIN decomposition

Notes already distinguish causes on V1R1:

| Cause | n |
|---|---:|
| CONTEXT_INSUFFICIENT | 84 |
| MULTIPLE_SEMANTIC_READINGS | 54 |
| DOMAIN_UNCERTAIN | 44 |
| RELATION_UNCERTAIN | 17 |

Useful for future supervision; **not** required to unblock now.

## 12. Minimum new-gold requirement

```text
NO_NEW_GOLD_REQUIRED
```

Materialize derived fields from existing subtype + final gold +
`required_evidence_present` / `missing_required_semantics`:

- `evidence_relation_present`
- `semantic_resolvable`
- `domain_relevant_derived` (=1 for current V1R1 NONE/PRESENT mass)

No new human settlement authority for the V1R1 training primitives.

## 13. Candidate-objective comparison

| Objective | Semantic correctness | New annotation | V1R1 | Shortcut risk | Complexity | Viable |
|---|---|---|---|---|---|---|
| A final class direct | FAIL — conflates axes | none | full | high SHORT_ATOM | current | no |
| B relation + uncertainty | PASS for V1R1 failure | derive | full | medium | low–medium | yes |
| C domain+relation+resolvable | PASS generally | needs DOMAIN_IRRELEVANT | partial | lower if domain negs exist | high | no now |
| D relation only + metadata | PASS minimum viable | none — derive | full | medium (mitigated by contract) | lowest viable | **yes / preferred** |

## 14. Semantic sufficiency (RELATION_ONLY)

| Case | Representable |
|---|---|
| domain-irrelevant prose | no (needs DOMAIN_IRRELEVANT mass absent from V1R1) |
| domain-relevant lexeme only | yes |
| domain-relevant short atom with explicit relation | yes |
| domain-relevant prose with no asserted relation | yes |
| explicit positive evidence | yes |
| negated relation | yes (as NO_EVIDENCE_RELATION / resolvable) |
| ambiguous relation | yes (`semantic_resolvable=0`) |
| insufficient context | yes (`semantic_resolvable=0`) |

Viable for the diagnosed mismatch. Domain-irrelevant prose remains an ontology
gap, not the Gate1 failure under audit.

## 15–18. Decisions

```text
PRIMARY_DECOMPOSITION = RELATION_ONLY_DECOMPOSITION
DATASET_CONSEQUENCE = ANNOTATION_ONLY_CHANGE
objective_change_justified = true
architecture_change_justified = false
```

Single new primitive `evidence_relation_present` (plus deterministic use of
existing subtype/final gold for domain + resolvability) is sufficient. A
three-axis redesign is not justified until `DOMAIN_IRRELEVANT` mass exists.

## Exact next action (not authorized)

```text
SPEC_STAGE_A_FACTORIZED_OBJECTIVE
```

Receipt:
`classification-v5-stage-a-semantic-decomposition-receipt-20261001.json`
(`93202898…`).
