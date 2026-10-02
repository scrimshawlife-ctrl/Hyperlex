# REASSESS_V6_FUNCTION_TASK_SIGNAL

Read-only diagnostic. No new function head. Encoder / NONE / DOMAIN /
MEDIATION / ontology frozen. QUAL-003 blocked. MODEL_WIDE_BEST unchanged.

```text
PRIMARY_DIAGNOSIS = FUNCTION_TASK_SIGNAL_PARTIAL
CEILING_CLASS     = TEXT_SIGNAL_CEILING
AXIS_STRUCTURE    = latent_pragmatic_attributes
TASK_SIGNAL_LIMIT = True
NEXT_ACTION       = REDESIGN_V6_FUNCTION_OBJECTIVE_AROUND_PRAGMATIC_SIGNAL

formulation FUNCTION macros (REP_V3, gated):
  OLD_SHARED_HEAD              = 0.2964
  INDEPENDENT_BINARY_VERIFIERS = 0.2938
  HYBRID_VERIFIER              = 0.3058
  FUNCTION_SEMANTIC_MATCHING   = 0.1721

mean consensus-fail share among gold = 0.640
mean pragmatic/context cue share     = 0.832
dual_annotator gold recovery         = 0.140
dual_annotator A/B agree             = 0.999
true_human_iaa_available             = False

function.conflictive_force   = CONTEXT_SENSITIVE
function.evaluative_stance   = CONTEXT_SENSITIVE
function.memetic_form        = CONTEXT_SENSITIVE
function.relational_intimacy = CONTEXT_SENSITIVE
```

Receipt: `bf5e25f1cc3792fa3d0d598671ecd9140ecd8116fdc6f2df6564ccd508ff100f`

## Per-function signal

| label | class | TRAIN/DEV/REP | old / ind / hyb F1 | NN purity | +/− margin | cooc | expl cue | prag/ctx | cons-fail |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| conflictive_force | CONTEXT_SENSITIVE | 111/30/62 | 0.321 / 0.326 / 0.252 | 0.40 | 0.13 | 0.02 | 0.10 | 0.82 | 0.68 |
| evaluative_stance | CONTEXT_SENSITIVE | 107/31/51 | 0.289 / 0.239 / 0.280 | 0.27 | 0.12 | 0.02 | 0.12 | 0.88 | 0.65 |
| memetic_form | CONTEXT_SENSITIVE | 123/22/46 | 0.265 / 0.262 / 0.385 | 0.43 | 0.21 | 0.02 | 0.13 | 0.83 | 0.50 |
| relational_intimacy | CONTEXT_SENSITIVE | 90/22/49 | 0.310 / 0.349 / 0.306 | 0.24 | 0.22 | 0.02 | 0.20 | 0.80 | 0.73 |

Support is adequate on all four (prior diversity expand settled). Multi-label
co-occurrence is near-zero (~0.02) — the labels are not soft-overlapping as
gold; the failure mode is pragmatic/context, not ontology collision.
Lexical explicit-cue share is low (0.10–0.20). Styles mix wikt + wiki-culture;
domain fanout 3–7.

## Cross-formulation error overlap

`TASK_SIGNAL_LIMIT = True`: mean share of gold positives failed by ≥3 of 4
formulations = **0.640**.

Pairwise FN Jaccard (old ↔ independent) is high on conflictive (0.87),
evaluative (0.80), intimacy (0.80); memetic lower (0.51) where hybrid lifts
recall. Competitive heads (old / independent / hybrid) cluster at
**0.294–0.306** macro-F1; semantic matching is an outlier at 0.172.
Same rows repeatedly fail across architectures → task-signal limit, not
wrong head shape.

## Human-vs-model boundary

True independent human IAA is still
`PROTOCOL_DEFINED_AWAITING_OPERATOR_ANNOTATION` (foundation). Dual-scheme
cue raters agree with each other (A/B ≈ 0.999) but recover only ~14% of
function gold — gold lives beyond the lexical cue protocol.

Cue mix on REP function positives (n≈208 label-instances):
world/background 74 · pragmatic inference 58 · discourse/context 41 ·
explicit lexical 28 · compositional 7.

Consensus FN rates by cue type stay high across the board (0.54–0.71),
including explicit lexical (0.64). Failures concentrate where the frozen
sentence encoding cannot carry pragmatic / world / discourse force, not
where support is missing.

## Signal / geometry

- Axis characterization: **latent_pragmatic_attributes** (task characterization
  only — no rename/merge).
- Geometry: positive-vs-hard-negative margins exist (0.12–0.22) and NN purity
  is middling (0.24–0.43), so some embedding structure is present, but it is
  not enough for useful reliability under text-only frozen-encoder heads.
- Independent verifiers change precision/recall tradeoffs (esp. memetic /
  intimacy) without lifting the macro ceiling — expected when signal is real
  but mostly pragmatic/context-sensitive.

## Ceiling

```text
CEILING_CLASS = TEXT_SIGNAL_CEILING
```

Evidence for a practical ceiling near ~0.30 macro-F1: three competitive
formulations converge within ~0.01; consensus fails dominate gold; pragmatic/
context cue share ≈ 0.83; diversity already adequate. No fabricated max score.
Not DATA_LIMITED (support ok). Not ANNOTATION_BOUNDARY (true IAA unavailable;
dual-rater self-consistency is high). Not NO_CLEAR_CEILING (no formulation
breaks away).

## Rejected micro-fixes

```text
another_function_head            = rejected
tune_thresholds                  = rejected
modify_ontology                  = rejected
add_function_data_by_default     = rejected
use_QUAL_003_for_optimization    = rejected
reopen_encoder_selection         = rejected
retrain_DOMAIN_or_MEDIATION      = rejected
modify_NONE_gate                 = rejected
```

## Primary diagnosis + next action

```text
PRIMARY_DIAGNOSIS = FUNCTION_TASK_SIGNAL_PARTIAL
NEXT_ACTION       = REDESIGN_V6_FUNCTION_OBJECTIVE_AROUND_PRAGMATIC_SIGNAL
```

Partial but usable: recoverable text-only signal exists (~0.30), no function
collapsed, support adequate — but the shared limit is pragmatic / contextual
semantics in the frozen representation, not head architecture.
