# Classification v5 — Stage-A negative-evidence surface

Parent failure: `HYPERLEX_CLASSIFICATION_V4_BALANCED_RESERVE_EVAL_V1` (`SETTLED_FAIL`,
`STAGE_A_NONE_GENERALIZATION_FAILURE`).

Design rule: `DESIGN_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE`

Surface rule: `HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1`

## Intent

Build a fresh Stage-A train/validation surface that teaches:

```text
EVIDENCE_PRESENT
vs
NO_EVIDENCE
vs
UNCERTAIN
```

with emphasis on semantically difficult NONE examples. This pass does **not**
train, does **not** score any reserve, and does **not** move BEST
(`9fba0f66…` remains UNCHANGED).

## Negative taxonomy

| Subtype | Gate label | `required_evidence_present` |
|---|---|---|
| `POSITIVE_EVIDENCE` | `EVIDENCE_PRESENT` | `true` |
| `ORDINARY_DOMAIN_NONE` | `NO_EVIDENCE` | `false` |
| `HARD_NONE` | `NO_EVIDENCE` | `false` |
| `NEAR_DOMAIN_NONE` | `NO_EVIDENCE` | `false` |
| `GENERIC_NONE` | `NO_EVIDENCE` | `false` |
| `LEXICAL_LOOKALIKE_NONE` | `NO_EVIDENCE` | `false` |
| `SHORT_ATOM_NONE` | `NO_EVIDENCE` | `false` |
| `AMBIGUOUS_EVIDENCE` | `UNCERTAIN` | `uncertain` |

`ORDINARY_DOMAIN_NONE` is the priority subtype: in-domain / domain-adjacent
prose that must not be treated as evidence present.

## Floors

Acquisition:

```text
POSITIVE_EVIDENCE >= 800
ORDINARY_DOMAIN_NONE >= 400
HARD_NONE >= 300
NEAR_DOMAIN_NONE >= 300
GENERIC_NONE >= 250
LEXICAL_LOOKALIKE_NONE >= 250
SHORT_ATOM_NONE >= 200
AMBIGUOUS_EVIDENCE >= 200
```

Validation:

```text
POSITIVE_EVIDENCE >= 150
ORDINARY_DOMAIN_NONE >= 80
HARD_NONE >= 60
NEAR_DOMAIN_NONE >= 60
GENERIC_NONE >= 50
LEXICAL_LOOKALIKE_NONE >= 50
SHORT_ATOM_NONE >= 40
AMBIGUOUS_EVIDENCE >= 40
```

## Leakage exclusions

Reject overlap with spent v2 / v3 / v4 reserve identities, historical held-out
surfaces, and measurement-only identities. `TRAIN_CONSUMED` hub rows remain
admissible for Stage-A surface rebuild.

## Split policy

Deterministic identity-based `train` / `validation` only. Paired
positive/negative examples share a `pair_group_id` and stay in the same split.

## Readiness

`READY` only when acquisition + validation floors pass, spent-reserve overlap
is zero, lineage/disjointness passes, schema checks pass, all subtypes are
represented, ordinary-domain coverage passes, and no critical surface shortcut
remains (length / surface / extreme bag-of-words diagnostics).

Otherwise remain `PREREGISTERED` with exact gaps.

## Frozen Stage-A train contract (only if READY)

Primary gate:

```text
false_evidence_entry_rate_on_none <= 0.05
```

Secondary:

```text
EVIDENCE_PRESENT recall >= 0.70
NO_EVIDENCE recall >= 0.90
```

Do not optimize family metrics until Stage A passes these gates.
`train_authorized` stays `false` until an explicit train authorization pass.

## Artifacts

Schema: `schemas/classification-v5/evidence_example.v1.schema.json`

Builder: `scripts/shadow/hyperlexical/classification_v5_stage_a_negative_evidence_surface.py`

Spark runner: `scripts/spark/run_classification_v5_stage_a_negative_evidence_surface.py`

Private seal (Spark):
`/home/morpheus/hlx-private/classification-v5-stage-a-negative-evidence-surface-20260930/`
