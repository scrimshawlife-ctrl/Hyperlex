# Classification v3 — readiness / state contract

Lifecycle (compact):

```text
DRAFT
PREREGISTERED
READY
RUNNING
SETTLED_PASS
SETTLED_FAIL
SETTLED_INVALID
```

## Current

```text
HYPERLEX_CLASSIFICATION_V3_EVIDENCE_GATE = PREREGISTERED
HYPERLEX_CLASSIFICATION_V2 = SETTLED_FAIL
surface = HYPERLEX_V3_EVIDENCE_SURFACE_V1 (build sealed under hlx-private)
BEST = UNCHANGED (9fba0f66…)
train_v3 = false
```

Preregistration freeze: `classification-v3-evidence-gate-preregistration.md`.

## Transition rules

| From | To | Requires |
|---|---|---|
| DRAFT | PREREGISTERED | schemas frozen; eval gate preregistered; spent-reserve exclusion pinned |
| PREREGISTERED | READY | admission surface built; disjointness proofs; no spent-reserve overlap |
| READY | RUNNING | explicit train authorization (separate pass) |
| RUNNING | SETTLED_* | validation + (if authorized) fresh reserve disposition |

## READY blockers (non-exhaustive)

```text
schemas missing or drifted
false_evidence_entry gate not preregistered
spent v2 reserve identities present in train/val
Stage-A/B/C invariant tests failing
ontology width ≠ forward 18 without explicit v3 ontology change auth
Jev not OFF unless separately authorized
```

## Explicit non-goals for DRAFT→PREREGISTERED

```text
do not train
do not score spent v2 reserve again
do not move BEST
do not acquire labeled mass before PREREGISTERED
```
