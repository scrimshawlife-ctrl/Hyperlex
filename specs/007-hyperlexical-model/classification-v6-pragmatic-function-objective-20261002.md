# REDESIGN_V6_FUNCTION_OBJECTIVE_AROUND_PRAGMATIC_SIGNAL

```text
OUTCOME           = V6_PRAGMATIC_OBJECTIVE_NOT_SUPPORTED
NEXT_ACTION       = REASSESS_V6_FUNCTION_PRODUCT_REQUIREMENT
selected_objective = null
selected_supervision = CUE_ONLY

identifiability_lift (prim − fun cue recovery) = 0.013
primitive_dual_agreement = 1.000
function_dual_agreement  = 1.000
gold_function_rows needing HUMAN_RESETTLEMENT  = 580/728 (0.797)
REP gold cue recovery: function 0.131 / primitive 0.150

primitive_macro_f1_vs_cue (REP) = 0.1885
derived FUNCTION (B/C)          = 0.1976
baseline FUNCTION               = 0.2964
false_function_emission         = 0.0314 (baseline 0.0529)
function_omission               = 0.7816
unresolved_rate (C)             = 0.1013

DOMAIN/MEDIATION frozen unchanged = true
NONE preserved = true
reason = primitives_not_more_reproducible_from_text
```

Receipt: `98cb72f1e2e8d922e3d261a34145cd0b38dfa1c057ee8b90d82dd6b33ada6b58`

## Proposed pragmatic primitives

| id | definition (text-observable) |
|---|---|
| `prag.normative_judgment` | praise / insult / pejoration / prestige / approval–disapproval language |
| `prag.intimate_partnership` | romantic / dating / sexual / intimate partnership evidence |
| `prag.hostile_force` | hostility / violence / combat / aggression framing |
| `prag.memetic_template` | meme format / copypasta / image macro / viral template markers |
| `prag.mockery_framing` | ridicule / satire / parody / joke-about framing |

Each is narrower than the settled function label, cue-annotatable, and independent of source metadata.

## Old-function → primitive mapping

| function | expression | product mode | derivation rule |
|---|---|---|---|
| evaluative_stance | one primitive | DERIVED_PREDICTION | require `normative_judgment`; mockery alone → unresolved |
| relational_intimacy | one primitive | DERIVED_PREDICTION | require `intimate_partnership` |
| conflictive_force | one primitive | DERIVED_PREDICTION | require `hostile_force` |
| memetic_form | primitive + contextual uncertainty | UNRESOLVED_WHEN_CONTEXT_MISSING | require `memetic_template`; mockery alone → unresolved |

No function remains a directly supervised four-way head target.

## Identifiability / annotation audit

All TRAIN/DEV/REP rows audited under the primitive schema (deterministic cues only; no large-scale relabel).

| status | all rows | gold-function rows |
|---|---:|---:|
| DIRECTLY_DERIVED | 4293 | 105 |
| HUMAN_RESETTLEMENT_REQUIRED | 580 | **580** |
| NOT_IDENTIFIABLE | 213 | 43 |

Cue-positive rows: TRAIN 125 · REP 64. Among gold-function rows, primary-primitive cue recovery is only **0.15** vs function-cue recovery **0.14** (lift **0.013**). The high-level function gold is largely not text-grounded — but the proposed lexical primitives do not recover it either.

## Human-agreement findings

True operator second-rater IAA remains
`PROTOCOL_DEFINED_AWAITING_OPERATOR_ANNOTATION`.

Dual cue-protocol agreement (all-cues vs strong-cues) is ≈1.0 for both
primitives and functions — the protocols are nearly coextensive on this
surface, so they do **not** show primitives as substantially more
reproducible than function cues. Per section 4: when primitives are not
substantially more reproducible from text, **reject the decomposition**.

## Primitive-model results (objective A)

Frozen encoder → independent binary MLPs on cue-derived primitives
(CUE_ONLY selected on DEV over CUE_PLUS_RULE).

REP macro-F1 vs cue gold: **0.188**

| primitive | P | R | F1 | support |
|---|---:|---:|---:|---:|
| normative_judgment | 0.14 | 0.56 | 0.227 | 9 |
| intimate_partnership | 0.27 | 0.33 | 0.298 | 21 |
| hostile_force | 0.29 | 0.35 | 0.314 | 23 |
| memetic_template | 0.08 | 0.11 | 0.091 | 9 |
| mockery_framing | 0.01 | 0.33 | 0.013 | 3 |

Sparse cue supervision + frozen sentence vectors do not yield a stable
primitive predictor.

## Derived-function results (B / C)

| objective | FUNCTION | system | false emission | omission | unresolved |
|---|---:|---:|---:|---:|---:|
| B derivation | 0.198 | 0.298 | 0.031 | 0.782 | 0 |
| C + abstention | 0.198 | 0.298 | 0.031 | 0.782 | 0.101 |
| old FUNCTION baseline | **0.296** | 0.331 | 0.053 | — | — |

False emission improves modestly; omission dominates. Resolved precision
under C ≈ 0.33 — not reliable. DOMAIN/MEDIATION match baseline exactly.
NONE gates preserved (zero-FP 0.083 / exact 0.917).

## Comparison / ceiling reading

The pragmatic-objective redesign lowers derived FUNCTION below the
~0.30 text-signal ceiling instead of clarifying it. Lexical primitives
inherited from the same cue families as the function labels do not create
a more learnable internal target under the frozen encoder.

## Rejected micro-fixes

```text
change_encoder                 = rejected
change_NONE_gate               = rejected
retrain_DOMAIN / MEDIATION     = rejected
change_ontology                = rejected
tune_on_QUAL                   = rejected
another_direct_function_head   = rejected
acquire_more_data_by_default   = rejected
```

## Primary diagnosis + next action

```text
OUTCOME     = V6_PRAGMATIC_OBJECTIVE_NOT_SUPPORTED
NEXT_ACTION = REASSESS_V6_FUNCTION_PRODUCT_REQUIREMENT
```

Hypothesis tested and rejected for this cue-primitive set: concrete
pragmatic cues were **not** shown to be substantially more text-reproducible
or learnable than the aggregate function labels, so Function cannot be
rescued by this internal decomposition alone without revisiting the
product requirement.
