# Classification v3 — evidence-gate architecture

Rule: `HYPERLEX_CLASSIFICATION_V3_EVIDENCE_GATE`  
State: `DRAFT` → target `PREREGISTERED` before any acquisition/training  
Predecessor: Classification v2 `SETTLED_FAIL` (see `classification-v2-final-settlement.md`)

This pass defines contracts only. **Do not train v3 here.** Do not reuse the spent v2 reserve. Do not move BEST.

## Architecture

```text
input
  -> Stage A: evidence detection
  -> Stage B: family candidate retrieval   (only if EVIDENCE_PRESENT)
  -> Stage C: selective decision
```

Canonical end-to-end outputs:

```text
NONE | FAMILY | AMBIGUOUS | ABSTAIN
```

Mapping:

```text
Stage A = NO_EVIDENCE     -> NONE
Stage A = UNCERTAIN       -> ABSTAIN
Stage A = EVIDENCE_PRESENT -> Stage B
  Stage B weak support              -> ABSTAIN
  Stage B multiple supported        -> AMBIGUOUS
  Stage B single strong candidate   -> FAMILY
```

Hard invariant: **only `EVIDENCE_PRESENT` may enter family retrieval.**  
`UNCERTAIN` must never map to `FAMILY_PRESENT` / retrieval.

## Stage A — Evidence detection

Question:

```text
Does this input contain sufficient positive lexical/domain evidence
to justify family retrieval?
```

Not: “is this somehow related to slang?” Not binary applicability.

### Returns

| Decision | Meaning |
|---|---|
| `NO_EVIDENCE` | No relevant active-family evidence |
| `EVIDENCE_PRESENT` | Sufficient positive evidence to justify retrieval |
| `UNCERTAIN` | Signal may exist; sufficiency unresolved |

### Feature / contract axes (inspectable)

| Axis | Role |
|---|---|
| positive lexical evidence | cues / spans that support ≥1 active family |
| domain-specificity | in-domain vs generic language |
| semantic specificity | concrete family-bearing sense vs vague adjacency |
| nearest positive-evidence support | similarity to train-side positive exemplars |
| negative / out-of-domain evidence | hard/near-domain/generic none support |

Frozen scalar gate:

```text
if evidence_score >= present_threshold: EVIDENCE_PRESENT
elif evidence_score <= none_threshold:  NO_EVIDENCE
else:                                   UNCERTAIN
```

Invariant: `none_threshold < present_threshold`. No silent middle→PRESENT collapse.

Schema: `hyperlex.classification.v3.evidence_decision.v1`

## Stage B — Candidate retrieval

Executes **only** when Stage A = `EVIDENCE_PRESENT`.

```text
retrieve top-K (K≤3) candidate families
from training-side positive exemplar evidence
```

Evidence-backed scores only. No forced family decision. No centroid-as-truth requirement; exemplar support remains first-class.

Schema: `hyperlex.classification.v3.family_candidates.v1`

## Stage C — Selective decision

| Output | Meaning |
|---|---|
| `NONE` | Stage A established no relevant evidence |
| `ABSTAIN` | Evidence uncertain or family support insufficient |
| `AMBIGUOUS` | Evidence present; multiple families remain supported |
| `FAMILY` | Evidence present; single sufficiently supported family |

Schema: `hyperlex.classification.v3.decision.v1`

## Explicit prohibitions (v2 failure modes)

v3 must not:

```text
forced 18-way argmax as semantic truth
reserve-derived thresholds
per-family validation threshold tuning
class-weight experimentation loops
prototype-only family semantics
using family retrieval to compensate for bad evidence gating
map UNCERTAIN -> EVIDENCE_PRESENT
invoke Stage B on NO_EVIDENCE or UNCERTAIN
reuse spent v2 reserve for train/val/promotion
```

## Dataset taxonomy

Training examples use subtype → gate label:

| subtype | gate label |
|---|---|
| `POSITIVE_EVIDENCE` | `EVIDENCE_PRESENT` |
| `HARD_NONE` | `NO_EVIDENCE` |
| `NEAR_DOMAIN_NONE` | `NO_EVIDENCE` |
| `GENERIC_NONE` | `NO_EVIDENCE` |
| `AMBIGUOUS_EVIDENCE` | `UNCERTAIN` |

`AMBIGUOUS_EVIDENCE` is ambiguity about **evidence sufficiency**, not Stage-C multi-family ambiguity.

Schema: `hyperlex.classification.v3.evidence_example.v1`  
Admission / hard-negative design: `classification-v3-dataset-admission.md`

## Evaluation (preregistered before train)

Primary gate (must pass before family metrics can authorize a **new** reserve):

```text
false_evidence_entry_rate_on_none <= 0.05
```

Preregistered at design time. **Not** derived from spent v2 reserve metrics. Rationale: product reliability bound (≤5% of gold-NONE rows may enter retrieval).

Also report: NO_EVIDENCE / EVIDENCE_PRESENT P/R/F1, UNCERTAIN rate, family emission precision/coverage, end-to-end NONE P/R, end-to-end selective accuracy.

Full contract: `classification-v3-evaluation.md`

## Reserve policy

The spent v2 classify reserve is **permanently diagnostic/history only**.  
v3 promotion requires a **new fresh sealed reserve** after internal validation passes the false-evidence-entry gate. Old reserve identities are forbidden from v3 train/validation/new-reserve admission.

## Forward-compatible v2 assets

Retained where compatible:

```text
18-family ontology
social-evaluation merge
cleaned training corpus / hub-filter concepts
boundary contracts
provenance OBSERVED|INFERRED
family exemplar index concepts
unbind architecture
BEST pin discipline / Jev OFF default
```

Not retained as canonical: v2 binary applicability semantics.

## Lifecycle

```text
DRAFT
PREREGISTERED
READY
RUNNING
SETTLED_PASS
SETTLED_FAIL
SETTLED_INVALID
```

Current: `DRAFT`. Next engineering action: freeze schemas + preregister evaluation (this pass), then acquire fresh evidence-gate training surface (later pass). No train in this pass.

## Readiness

See `classification-v3-readiness.md`.
