# Classification v5 — REMEDIATE_V5_UNCERTAIN_SURFACE

`REMEDIATE_V5_UNCERTAIN_SURFACE`

Parent diagnosis: **`MIXED_UNCERTAIN_SURFACE_FAILURE`** (UNCERTAIN label-surface
audit). Parent READY surface V1R8 dataset `c0fdd82d…` preserved unchanged.

Replacement surface: `HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R9`
dataset `8d4be830…` → **READY**.

Gate rule (frozen, unmodified): `HYPERLEX_V5_STAGE_A_SURFACE_READINESS_GATES_V1`
plus UNCERTAIN-specific readiness gates from this remediation CLEAR.

This pass does **not** train, does **not** score a reserve, does **not**
move BEST (`9fba0f66…` UNCHANGED), does **not** change architecture, and does
**not** acquire/reject/relabel from checkpoint probabilities.

## Remediation actions

1. Drop prior narrow UNCERTAIN bank (244 rows, almost all INFERRED ATOM /
   `MULTIPLE_PLAUSIBLE_INTERPRETATIONS` only).
2. Acquire fresh OBSERVED UNCERTAIN from Wiktionary, Wikipedia, and hub
   OBSERVED texts across all five frozen ambiguity reasons.
3. Fill remaining slots with curated INFERRED UNCERTAIN prose/atoms
   (semantic ambiguity by construction; not model-driven).
4. Enforce OBSERVED / ATOM–PROSE / source-family caps; preserve V1R8
   PRESENT/NONE splits so original readiness gates do not regress.
5. Freeze-encoder embedding hardness + semantic-placement diagnostics on BEST.
6. Joint original V5 + UNCERTAIN readiness re-eval → **READY**.

## Counts

| Split | n |
|---|---|
| train | 4437 |
| validation | 2051 |
| **total** | **6488** |

UNCERTAIN total **442** (train 280 / validation 162).
OBSERVED share **0.704**; validation OBSERVED share **0.728**.

## UNCERTAIN by ambiguity reason

| Reason | train | val | obs train | obs val |
|---|---:|---:|---:|---:|
| INSUFFICIENT_CONTEXT | 57 | 43 | 57 | 43 |
| CONFLICTING_EVIDENCE | 58 | 41 | 32 | 26 |
| PARTIAL_REQUIRED_CORE | 52 | 30 | 27 | 21 |
| MULTIPLE_PLAUSIBLE_INTERPRETATIONS | 67 | 33 | 46 | 19 |
| UNRESOLVED_SOURCE_MEANING | 46 | 15 | 31 | 9 |

## Surface / source

- ATOM share train/val: 0.179 / 0.235 (≤ 0.60)
- PROSE share train/val: 0.796 / 0.728 (≥ 0.20)
- Max source-family share: 0.301 (≤ 0.35)
- Val max source-family share: 0.296 (≤ 0.30)

## Semantic placement (frozen BEST CLS)

| Class | rate |
|---|---:|
| CENTERED_BETWEEN | 0.857 |
| PRESENT_LIKE | 0.113 |
| NONE_LIKE | 0.029 |
| ISOLATED | 0.000 |

## Boundary

`PRESENT_UNCERTAIN_BOUNDARY_CONFLICT = false`
(39 prior GENUINELY_UNCERTAIN PRESENT FNs remain gold PRESENT).

## Disjointness

identity / source-hash / parent-lineage / cross-split near-dup clusters = 0.

## Private artifacts

`hlx-private/classification-v5-stage-a-negative-evidence-surface-v1r9-20260930/`

## Next action

```text
FINAL_STATE = READY
NEXT_ACTION = AUTHORIZE_V5_STAGE_A_NEXT_RUN_ON_REMEDIATED_SURFACE
```

`train_authorized` remains false until a fresh train authorization step on
the V1R9 surface.
