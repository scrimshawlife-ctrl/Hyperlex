# Classification v5 — Stage-A factorized relation objective V1

```text
OBJECTIVE_ID = HYPERLEX_V5_STAGE_A_FACTORIZED_RELATION_OBJECTIVE_V1
RULE = SPEC_STAGE_A_FACTORIZED_OBJECTIVE
FACTORIZED_OBJECTIVE_SPEC = FROZEN
ANNOTATION_DERIVATION = SEALED
TRAIN_AUTHORIZED = false
ARCHITECTURE_CHANGE_REQUIRED = false
PARENT_DECOMPOSITION = RELATION_ONLY_DECOMPOSITION
PRIMARY_DIAGNOSIS = GATE1_SEMANTIC_TARGET_MISMATCH
V1R1 = 4095036e…
FACTORIZED_ANNOTATION_SHA256 = 4ac88450…
OBJECTIVE_RECEIPT = 45746d70…
STAGE_A_BEST = cd2829c1… UNCHANGED
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
V1R2 = NOT_CREATED
RESERVE = SPENT / unused
NEXT_ACTION = AUTHORIZE_STAGE_A_FACTORIZED_RELATION_TRAIN
NEXT_ACTION_AUTHORIZED = false
```

Spec + derived annotation sidecar only. No train, V1R2, human relabel,
Stage-B mutation, spent-reserve use, or BEST moves.

## Objective

Replace overloaded Gate-1 target `NO_EVIDENCE vs POSSIBLE_EVIDENCE` with:

| Head | Labels | Question |
|---|---|---|
| A — EVIDENCE_RELATION | NO_EVIDENCE_RELATION=0 / EVIDENCE_RELATION_PRESENT=1 | Does the text assert/instantiate the required evidence relation? |
| B — SEMANTIC_RESOLVABILITY | UNRESOLVABLE=0 / RESOLVABLE=1 | Is the evidence judgment semantically resolvable from the text? |

`POSSIBLE_EVIDENCE` is **`DEPRECATED_AS_STAGE_A_TRAINING_TARGET`**. Historical
two-stage artifacts retained.

## Critical semantic rule

```text
RELATION_HEAD_POSITIVE
  = asserted/instantiated evidence relation
  ≠ domain relevance | family cue | lexeme presence
    | source membership | dictionary headword
```

Short atoms are relation-positive only when gold is `POSITIVE_EVIDENCE`.

## Derived annotation mapping (sidecar only)

| Subtype | relation | resolvable | domain_derived |
|---|---|---|---|
| POSITIVE_EVIDENCE | 1 | 1 | 1 |
| ORDINARY_DOMAIN_NONE | 0 | 1 | 1 |
| LEXICAL_LOOKALIKE_NONE | 0 | 1 | 1 |
| SHORT_ATOM_NONE | 0 | 1 | 1 |
| NEAR_DOMAIN_NONE | 0 | 1 | 1 |
| HARD_NONE | 0 | 1 | 1 |
| AMBIGUOUS_EVIDENCE | MASKED | 0 | UNKNOWN |
| other | FAIL_CLOSED | — | — |

`domain_relevant_derived` is metadata only — **not** in the V1 loss.

## Exact derived counts (V1R1)

| Quantity | n |
|---|---:|
| rows | 3585 |
| relation positive | 1535 |
| relation negative | 1851 |
| relation masked | 199 |
| resolvable positive | 3386 |
| resolvable negative | 199 |
| relation-loss eligible | 3386 |
| resolvability-loss eligible | 3585 |
| duplicate identities | 0 |
| unsupported subtype derivations | 0 |

## Loss / masks

```text
L_total = L_relation + 1.0 * L_resolvability
```

- Relation CE: only where `semantic_resolvable == 1`
- Resolvability CE: all valid Stage-A rows
- Provenance weights: OBSERVED=1.0, INFERRED=0.5 (per-head eligible rows)
- Class weights: resolve later per head from train split only; do not reuse Gate1/Gate2 weights
- No focal loss

## Architecture

```text
shared ModernBERT encoder
CLS pooling
relation_head: hidden → 2 logits
resolvability_head: hidden → 2 logits
trainable: last 2 encoder layers + both heads
```

Not an architecture redesign — topology unchanged; head semantics/objective change.
No MLP / attention block / retrieval / prototype / domain / family head.

## Deterministic final decision

```text
if P(RESOLVABLE) < resolvability_threshold:
    UNCERTAIN
elif P(EVIDENCE_RELATION_PRESENT) >= relation_threshold:
    EVIDENCE_PRESENT
else:
    NO_EVIDENCE
```

Threshold grids (future validation only; not chosen here):

```text
{0.50,0.55,...,0.95} × {0.50,0.55,...,0.95} = 100 pairs
```

## Acceptance / diagnostics

Hard gates unchanged:

```text
false_evidence_entry_rate_on_none <= 0.05
EVIDENCE_PRESENT recall >= 0.70
NO_EVIDENCE recall >= 0.90
```

Diagnostic: UNCERTAIN recall; relation/resolvability macro-F1; relation FPR on
`SHORT_ATOM_NONE`; relation recall on SHORT_ATOM PRESENT.

Scientific test: does relation supervision improve SHORT_ATOM NONE rejection
without destroying SHORT_ATOM PRESENT recall?

## Known limitation

```text
DOMAIN_IRRELEVANT_GENERALIZATION = NOT_ESTABLISHED
```

V1R1 has no `GENERIC_NONE` mass. This objective is validated for
domain-relevant NO_RELATION vs RELATION_PRESENT vs semantic uncertainty.

## Stage-B compatibility

Unchanged: PRESENT→B permitted; NONE→stop; UNCERTAIN→abstain.

## Artifacts

| Artifact | Role |
|---|---|
| `stage_a_factorized_annotation.v1.schema.json` | sidecar schema |
| `classification_v5_stage_a_factorized_objective.py` | frozen contract |
| `build_classification_v5_stage_a_factorized_annotations.py` | deterministic builder |
| `FACTORIZED_ANNOTATIONS.jsonl` | sealed sidecar (`4ac88450…`) |
| `FACTORIZED_ANNOTATION_MANIFEST.json` | manifest |
| `DERIVATION_WITNESS.json` | integrity witness |
| `ARTIFACT_HASHES.json` | hash set |
| receipt JSON / this MD | sealed spec |

Private mirror:
`/home/morpheus/hlx-private/classification-v5-stage-a-factorized-objective-v1-20261001/`

## Exact next action (not authorized)

```text
AUTHORIZE_STAGE_A_FACTORIZED_RELATION_TRAIN
```
