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
HYPERLEX_CLASSIFICATION_V3_EVIDENCE_GATE = SETTLED_FAIL
HYPERLEX_CLASSIFICATION_V2 = SETTLED_FAIL
surface = HYPERLEX_V3_EVIDENCE_SURFACE_V1 READY
Stage A/B validation = PASS
fresh v3 reserve = RESERVE_FAIL (n=109; false_entry=0.25; emission=0.0)
AVAILABLE classify identities = 0
spent v3 reserve identities = 109 (evaluation_spent)
prior aborted v4 acquire identities = 173 (evaluation_spent; private seal removed)
HYPERLEX_CLASSIFICATION_V4_BALANCED_RESERVE_ACQUIRE_V1 = ACQUIRE_READY
  n=176 (none=48, present=128, distinct_families=16, max_family_share=0.0625)
  rows_sha256 = dd224047…794eb82
  receipt_sha256 = 1998f409…1bae9f5
BEST = UNCHANGED (9fba0f66…)
```

Preregistration freeze: `classification-v3-evidence-gate-preregistration.md`.  
Surface / Stage A / Stage B / Reserve receipts: `classification-v3-*-receipt-20260930.json`.  
Final settlement: `classification-v3-final-settlement.md`.  
Balanced acquire: `classification-v4-balanced-reserve-acquire.md` +
`classification-v4-balanced-reserve-acquire-receipt-20260930.json`.  
Next: separate auth for evidence-gate climb + one-shot score of this acquire pool.

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
