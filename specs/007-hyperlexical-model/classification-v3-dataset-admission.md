# Classification v3 — evidence-gate dataset & admission

Companion to `classification-architecture-v3.md`. State: `PREREGISTERED` (see `classification-v3-evidence-gate-preregistration.md`).

## Purpose

Build a training surface that contrasts evidence sufficiency explicitly, preventing:

```text
NONE -> false positive evidence -> downstream family sink
```

Do **not** mine or train on the spent v2 reserve. Fresh training-side identities only.

## Example taxonomy

| subtype | gate label | Meaning |
|---|---|---|
| `POSITIVE_EVIDENCE` | `EVIDENCE_PRESENT` | Direct evidence for ≥1 active family |
| `HARD_NONE` | `NO_EVIDENCE` | Lexically plausible but outside active-family semantics |
| `NEAR_DOMAIN_NONE` | `NO_EVIDENCE` | Domain-adjacent language without active-family signal |
| `GENERIC_NONE` | `NO_EVIDENCE` | Generic explanatory / ordinary language |
| `AMBIGUOUS_EVIDENCE` | `UNCERTAIN` | Some signal; sufficiency unresolved |

Provenance remains `OBSERVED` | `INFERRED`.

Schema: `schemas/classification-v3/evidence_example.v1.schema.json`

## Hard-negative requirements

Fresh examples must include:

```text
lexically similar but semantically NONE
domain-adjacent but outside active families
generic explanatory prose
short lexical atoms with no active-family evidence
```

These populate `HARD_NONE`, `NEAR_DOMAIN_NONE`, and `GENERIC_NONE`. They are first-class training mass, not an afterthought filter.

## Deterministic admission rules

1. Identity = `normalized_text_sha256(text)` (same Hyperlex normalizer as holdout/reserve).
2. Refuse if identity appears in:
   - spent v2 classify EVAL_RESERVE identity list
   - any sealed v2 measurement / settlement surface marked spent
   - held-out manifests active for the experiment
3. Refuse duplicate identities across splits (train / validation / future v3 reserve).
4. `POSITIVE_EVIDENCE` requires `evidence_label=EVIDENCE_PRESENT` and non-empty `candidate_families` ⊆ forward 18-family ontology.
5. `HARD_NONE` / `NEAR_DOMAIN_NONE` / `GENERIC_NONE` require `evidence_label=NO_EVIDENCE` and empty candidate family emission intent (candidates may be empty or diagnostic-only; must not authorize Stage B).
6. `AMBIGUOUS_EVIDENCE` requires `evidence_label=UNCERTAIN`.
7. Spans: if present, `0 ≤ start < end ≤ len(text)`.
8. Split assignment is sealed before training; validation identities never enter train.
9. Jev stays OFF for admission mining unless a separate authorization opens shadow mode (default: refuse Jev-gated rows).

## Disjointness

```text
v3_train ∩ v3_validation = ∅
v3_train ∪ v3_validation ∩ spent_v2_reserve = ∅
v3_train ∪ v3_validation ∩ future_v3_reserve = ∅  (when reserve is later sealed)
```

## Carry-forward from v2 (non-label)

May reuse as *sources for fresh labeling*, after re-admission under v3 evidence labels:

- forward 18-family ontology texts (re-label evidence, do not assume FAMILY_PRESENT)
- boundary / definition prose as POSITIVE_EVIDENCE candidates when clearly family-bearing
- hub-filtered civilian rows only after evidence relabel + spent-reserve exclusion

Must not copy v2 applicability targets as v3 evidence labels.

## Lifecycle for the surface

```text
DRAFT -> PREREGISTERED -> READY -> RUNNING -> SETTLED_*
```

No acquire until schemas and evaluation gate are PREREGISTERED.
