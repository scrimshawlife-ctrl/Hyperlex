# Semantic evidence v2

Workstream B is `SEMANTIC_EVIDENCE_SUCCESSOR_DESIGN`. Its rule name is `RUNE.SEMANTIC_COMPOSITIONALITY_EVIDENCE.v2`. It does not repair `RUNE.SEMANTIC_COMPOSITIONALITY_THRESHOLD.v1` or `.v2`.

v1 remains `CLOSED_CALIBRATION_DESIGN_INSUFFICIENT`. v2 remains `NO_THRESHOLD_PASSES_PRECISION_GATE`. The governing conclusion is `CURRENT_RESIDUAL_REPRESENTATION_INSUFFICIENT_FOR_REQUIRED_PRECISION`, not `THRESHOLD_SEARCH_INSUFFICIENT`.

Observed on the frozen v2 support join: ready HIGH 13, ready SECONDARY 22, direction HIGH greater than SECONDARY, descriptive AUC 0.580420, rank-biserial 0.160839, precision-floor candidates 2, Wilson-qualified candidates 0, fully qualified candidates 0. The threshold value stays null. Measurement stays sealed. Training stays unauthorized.

## Research question

Can a frozen multi-feature semantic evidence function distinguish supplied-sense lexicalized noncompositional expressions from lexicalized or ordinary compositional expressions with enough precision to satisfy the existing Hyperlex safety gates?

That question is unanswered. This document drafts the experiment. It does not preregister a model revision, draw a surface, or open a threshold lane.

## Architecture

The successor starts from the supplied PWN 3.0 parent sense and frozen constituent senses. It abstains when constituent structure is unresolved. It builds an evidence feature vector from whole-expression and constituent-composition views, then, only after that vector is frozen, evaluates an interpretable calibrator. The output vocabulary is YES or UNKNOWN. There is no semantic NO unless a later preregistration adds one.

REJECT and QUARANTINE stay safety vetoes. They are not negative training classes for the calibrator.

A single scalar `1 - cosine(whole, normalized mean of constituents)` remains the historical baseline. It is not assumed to be sufficient.

## Separate state

This lane does not share a state machine with threshold-artifact schema hardening. The current state is `SEMANTIC_EVIDENCE_V2_SPEC_DRAFTED`. The next named transition is `SEMANTIC_EVIDENCE_V2_PREREGISTERED`. This draft does not authorize it.

The v2 measurement surface disposition is `RETAIN_FOR_V2_ONLY`. It is not reused here.

## Non-authorization

This specification does not authorize a threshold-v2 redesign, redraw, or measurement execution. It does not change the 0.80 precision floor, the Wilson floor, or the safety vetoes. It does not authorize SELECT-005, training, BEST promotion, runtime integration, admission, settlement, or gold mutation. It does not draw `DEVELOPMENT_V2`, `CALIBRATION_V3`, or `MEASUREMENT_V3`. The raw size target of 300 rows per layer is a design note, not a draw.

Companion contracts:

- `semantic-evidence-v2-state-machine.md`
- `semantic-evidence-v2-data-contract.md`
- `semantic-evidence-v2-evaluation-contract.md`
