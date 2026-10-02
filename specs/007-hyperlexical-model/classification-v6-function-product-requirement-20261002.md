# REASSESS_V6_FUNCTION_PRODUCT_REQUIREMENT

```text
PRODUCT_DISPOSITION = FUNCTION_RETAIN_OPTIONAL
NEXT_ACTION         = HARDEN_V6_CORE_PRODUCT_WITHOUT_REQUIRED_FUNCTION
selected_alternative = B_MAKE_FUNCTION_OPTIONAL_BEST_EFFORT
rationale = text_only_ceiling_insufficient_for_required_axis;concepts_retained_as_advisory_best_effort;core_product_is_gate_domain_mediation

revised required outputs:
  evidence_gate, domain, mediation
optional:
  function_best_effort

core_system_macro_f1 (DOMAIN+MEDIATION) = 0.3484
three-axis system_macro_f1 (reference)  = 0.3311
NONE zero-FP / exact                   = 0.0877 / 0.9123
hierarchy_violation_rate               = 0.001985
FUNCTION_blocks_release = false
```

Receipt: `c488a39dbc5208affbd5a2a1433f7ea01e3f88996abb8a16c84716fa57ad14f2`

## Product rationale

Repeated modeling evidence shows FUNCTION labels are human-coherent but
not reliably recoverable from text-only input under the current contract:
direct heads ≈0.296, independent verifiers ≈0.294, hybrid ≈0.306,
semantic matching ≈0.172, cue-primitives ≈0.189 / derived FUNCTION ≈0.198.
Ceiling class TEXT_SIGNAL_CEILING; pragmatic objective NOT_SUPPORTED.
Incorrect function emission is costly (esp. memetic FP). Omission is
preferable to false product claims. NONE, DOMAIN, and MEDIATION remain
viable and form a coherent core without required FUNCTION.

## Per-function disposition

| function | disposition | placement | best F1 | baseline P | prag/ctx | FP cost |
|---|---|---|---:|---:|---:|---|
| evaluative_stance | KEEP_OPTIONAL | HUMAN_ANNOTATION_ONLY,CONTEXTUAL_ENRICHMENT,DOWNSTREAM_REASONING_ONLY | 0.289 | 0.375 | 0.88 | high |
| relational_intimacy | KEEP_OPTIONAL | HUMAN_ANNOTATION_ONLY,CONTEXTUAL_ENRICHMENT | 0.349 | 0.500 | 0.80 | high |
| conflictive_force | KEEP_OPTIONAL | HUMAN_ANNOTATION_ONLY,CONTEXTUAL_ENRICHMENT | 0.326 | 0.360 | 0.82 | high |
| memetic_form | KEEP_RESEARCH_ONLY | HUMAN_ANNOTATION_ONLY,CONTEXTUAL_ENRICHMENT | 0.385 | 0.297 | 0.83 | very_high |

## Contract alternatives

- **A mandatory** — rejected: ~0.30 ceiling does not satisfy required-axis need.
- **B optional / best-effort** — **selected**: core = gate + DOMAIN + MEDIATION;
  FUNCTION emitted only as advisory when evidence/confidence sufficient.
- **C contextual reasoning** — preserved as research track (not V6 core blocker).
- **D full remove** — rejected for now: concepts retain optional/research value.

## V6 product without required FUNCTION

- DOMAIN macro-F1 = 0.3548
- MEDIATION macro-F1 = 0.3421
- core system macro-F1 = 0.3484 (≥ 0.30 floor)
- NONE rejection: zero-FP 0.0877, exact 0.9123
- hierarchy violation rate ≈ 0.001985
- QUAL-003 not rescored (EVALUATION_SPENT); gates updated so FUNCTION
  no longer blocks release / system macro.

## Release-gate effects

```text
system_macro_axes = domain, mediation
FUNCTION_axis_gate = not_required
FUNCTION_reporting = advisory_only
FUNCTION_blocks_release = false
ontology function labels = preserved (concepts/research/annotation)
```

## Preserved research findings

- `FUNCTION_TASK_SIGNAL_PARTIAL`
- `TEXT_SIGNAL_CEILING≈0.30_macro_F1`
- `V6_PRAGMATIC_OBJECTIVE_NOT_SUPPORTED`
- `direct_heads_and_independent_verifiers_converged`
- `semantic_matching_underperformed`
- `cue_primitive_decomposition_rejected`
- `NONE_DOMAIN_MEDIATION_remain_viable`
- `QUAL-003_EVALUATION_SPENT_not_rescored`
- `ontology_function_labels_preserved_as_concepts`

## Rejected micro-fixes

```text
train_another_function_model = rejected
change_encoder / NONE / DOMAIN / MEDIATION / ontology = rejected
rescore_QUAL = rejected
```

## Primary disposition + next action

```text
PRODUCT_DISPOSITION = FUNCTION_RETAIN_OPTIONAL
NEXT_ACTION         = HARDEN_V6_CORE_PRODUCT_WITHOUT_REQUIRED_FUNCTION
```

No function model trained. Encoder / NONE / DOMAIN / MEDIATION / ontology frozen.
MODEL_WIDE_BEST unchanged.
