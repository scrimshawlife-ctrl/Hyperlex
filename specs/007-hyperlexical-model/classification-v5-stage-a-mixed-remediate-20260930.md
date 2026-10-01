# Classification v5 — Stage-A mixed-failure remediation

`REMEDIATE_V5_STAGE_A_MIXED_FAILURE_V1`

Parent diagnosis: **`MIXED_STAGE_A_FAILURE`** / controlled interpretation
`INSUFFICIENT_MATCHED_SUPPORT` (receipt `246bbae7…`, SELECTED `3b1b574a…`).

Parent READY surface: `HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R7`
dataset `a81ca68a…`.

Replacement surface: `HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R8`
dataset `c0fdd82d…` → **READY**.

Gate rule (frozen, unmodified): `HYPERLEX_V5_STAGE_A_SURFACE_READINESS_GATES_V1`.

This pass does **not** train, does **not** score a reserve, does **not**
move BEST (`9fba0f66…` UNCHANGED), and does **not** change architecture or
thresholds.

## Scientific interpretation preserved

| Quantity | Value |
|---|---|
| OBSERVED/INFERRED raw false-entry delta | +0.132 |
| matched delta | +0.120 |
| CI95 | [0.069, 0.176] |
| matched coverage | 0.418 |
| matched n | 302 |
| PROVENANCE_ASSOCIATION | OBSERVED |
| PROVENANCE_CAUSALITY | NOT_ESTABLISHED |

Remediation does **not** assume provenance causes the failure. It repairs the
support distribution on both sides of the mixed failure.

## Remediation actions

1. Fresh OBSERVED ordinary-domain NONE acquisition (Wiktionary + Wikipedia)
   with expanded domains (priority anatomy / chemistry / astronomy; also
   pharmacology, mineralogy, mycology, entomology, archaeology, paleontology,
   linguistics, architecture). Acquire n=1013 (ordinary=650, PRESENT=352).
2. Source-family diversification: Wikipedia leads stamped `v5_src_wp_*` so
   ordinary OBSERVED is not carried only by implicated `v5_src_wik_*` shards
   (ordinary OBSERVED wiki share 0.644; Wikipedia share 0.347).
3. PRESENT support fills for diagnosis-underrepresented families
   (workplace-career, conflict-aggression, politics-civic, regional-cultural,
   social-evaluation, internet-slang, …).
4. Component-level re-split that **reserves** train OBSERVED floors:
   ordinary OBSERVED ≥ 160, PRESENT OBSERVED ≥ 140 (V1R7 had ordinary
   train OBSERVED = 0).
5. Pairing / source-cap / surface-balance / near-dup collapse under frozen
   methods; frozen-encoder embedding hardness on BEST ModernBERT CLS.
6. Full exact-gate re-eval → **READY** (12/12 mandatory gates).

## Counts

| Split | n |
|---|---|
| train | 4340 |
| validation | 1950 |
| **total** | **6290** |

Train ordinary OBSERVED: **160** (was 0).
Train PRESENT OBSERVED: **140** (was 80).

Cross-split exact identity overlap = 0; cross-split near-dup clusters = 0.

## Private artifacts

`hlx-private/classification-v5-stage-a-negative-evidence-surface-v1r8-20260930/`

## Next action

```text
FINAL_STATE = READY
NEXT_ACTION = TRAIN_V5_STAGE_A_ONCE
```

`train_authorized` remains false until a fresh train authorization step on
the V1R8 surface.
