# Semantic evidence v2 state machine

This machine belongs only to `RUNE.SEMANTIC_COMPOSITIONALITY_EVIDENCE.v2`.

```text
SEMANTIC_EVIDENCE_V2_SPEC_DRAFTED
  -> SEMANTIC_EVIDENCE_V2_PREREGISTERED
  -> DEVELOPMENT_SURFACE_FROZEN
  -> REPRESENTATION_EVALUATION_COMPLETE
  -> REPRESENTATION_SELECTED
  -> CALIBRATION_SURFACE_FROZEN
  -> CALIBRATION_COMPLETE
  -> THRESHOLD_FROZEN
  -> MEASUREMENT_EXECUTED
```

Failure states:

```text
INSUFFICIENT_RESOLUTION_COVERAGE
NO_REPRESENTATION_IMPROVEMENT
NO_DIRECTIONAL_SIGNAL
CALIBRATION_CONFOUND_REVIEW
NO_THRESHOLD_PASSES_PRECISION_GATE
MEASUREMENT_FAILURE
```

Current state: `SEMANTIC_EVIDENCE_V2_SPEC_DRAFTED`.

`SEMANTIC_EVIDENCE_V2_PREREGISTERED` is not authorized. Preregistration has to freeze model name, revision, artifact hashes, tokenizer hash, template hash, dtype, device class, batch size, seed, threading, feature definitions, and composition-function version before any evaluation. Those revisions are not frozen in this draft. The maximum comparison is three representation families: MiniLM baseline, ModernBERT sentence or gloss pooling, and one domain-neutral encoder with strong STS behavior. No open-ended model search.

`THRESHOLD_V2_CALIBRATION` may be read for postmortem and for feature hypothesis generation. If those rows are used to choose the successor architecture, they are `EVAL_SPENT` for any later threshold selection. They are not a clean calibration surface.

Development, calibration, and measurement identities and synsets for the successor must be disjoint from each other and must not automatically include the sealed v2 measurement surface. Its disposition stays `RETAIN_FOR_V2_ONLY` until a separate governance decision says otherwise.

No trainable composition layer and no model fine-tune belong in the first evidence evaluation. The goal of that evaluation is representational sufficiency before a predictor is trained.
