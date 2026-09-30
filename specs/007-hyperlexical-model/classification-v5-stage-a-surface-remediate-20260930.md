# Classification v5 — Stage-A surface remediation (`REMEDIATE_V5_STAGE_A_SURFACE_V1`)

Parent failed surface (exact gates): `HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1`
dataset `3add3aa6…` → **PREREGISTERED**.

Replacement surface: `HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R7`
dataset `a81ca68a…` → **READY**.

Gate rule (frozen, unmodified): `HYPERLEX_V5_STAGE_A_SURFACE_READINESS_GATES_V1`.

This pass does **not** train, does **not** score a reserve, and does **not**
move BEST (`9fba0f66…` UNCHANGED).

## Remediation actions

1. Component-level re-split via frozen
   `hlx.v5.near_duplicate.normalized_jaccard_v1` (pairs co-located).
2. Within-split near-dup collapse (one strongest admissible rep / component).
3. Paired NONE fills to floors (ORDINARY / NEAR / HARD).
4. Fresh OBSERVED Wiktionary acquires (n=414) for validation provenance.
5. Topic / ai-native / source-share repairs; shared-vocab lexical overlap.
6. Surface length / punctuation / definition-style repairs without rewriting
   source text.
7. Frozen-encoder embedding hardness on BEST ModernBERT CLS.
8. Full exact-gate re-eval → **READY**.

## Counts

| Split | n |
|---|---|
| train | 4489 |
| validation | 1388 |
| **total** | **5877** |

Subtype totals meet all acquisition floors. Validation OBSERVED fraction
`0.520`; ordinary-domain OBSERVED fraction `0.757`.

## Private artifacts

`hlx-private/classification-v5-stage-a-negative-evidence-surface-v1r7-20260930/`

Includes dataset, split manifest, component-split witness, deduplication
witness, pairing / provenance witnesses, topic/source balance report, surface
diagnostics, embedding hardness, GATE_EVAL, READINESS, ARTIFACT_HASHES.

## Next action

```text
surface_state = READY
next_action = TRAIN_V5_STAGE_A_ONCE
```

`train_authorized` remains false until the train authorization step.
