# Classification v5 — CLEAR audit of mixed-failure remediation

```text
CLEAR request = REMEDIATE_V5_STAGE_A_MIXED_FAILURE
REMEDIATION_STATUS = ALREADY_COMPLETE
SURFACE = HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R8
DATASET_SHA256 = c0fdd82d1734585a7d852318ac5b390cc5e2c50908c0ef9f9eba4b3f7ebedc8b
FINAL_STATE = READY
TRAIN = false
BEST = UNCHANGED
RESERVE = unused
```

This CLEAR re-issued the mixed-failure remediation whose authoritative seal is
already on branch `cursor/select-001-holdout-admit-41af`
(`classification-v5-stage-a-mixed-remediate-receipt-20260930.json`,
receipt `e61621af…`).

Parent failed experiment was **not** mutated:

| Pin | Value |
|---|---|
| Parent dataset | `a81ca68a…` (V1R7) |
| Training config | `4d2eaabd…` |
| SELECTED checkpoint | `3b1b574a…` |
| Diagnostic receipt | `246bbae7…` |
| Parent diagnosis | `MIXED_STAGE_A_FAILURE` |

Replacement surface V1R8 is READY under frozen
`HYPERLEX_V5_STAGE_A_SURFACE_READINESS_GATES_V1` (12/12). No architecture
change, no train in the remediation pass, reserve unused, BEST unchanged.

## Mission checklist vs sealed V1R8

| Requirement | Status |
|---|---|
| Preserve failed experiment pins | PASS |
| New versioned surface | PASS (`V1R8`) |
| Fresh OBSERVED ordinary NONE + source diversify | PASS (acquire n=1013; WP stamped) |
| anatomy/chemistry/astronomy OBSERVED ordinary ≥25, ≥2 families | PASS (61/51/67; wik+wp each) |
| +PRESENT support (OBSERVED fills) | PASS (PRESENT total 1240; OBSERVED 685; train OBSERVED 140) |
| Frozen 12 readiness gates | PASS |
| No model-driven filtering / no train / no reserve / no BEST move | PASS |
| Ordinary `v5_src_wik_*` aggregate ≤ 0.35 | **RESIDUAL** (0.644) — reported in V1R8 seal; **not** a frozen readiness gate |
| Controlled matched coverage ≥ 0.60 | **NOT_COMPUTABLE** from surface receipts (diagnosis matched coverage was 0.418 on V1R7 eval) |
| Ordinary ≥20 in every PRESENT topic_domain with support ≥20 | **NOT_MET for slang-family topic_domains** (PRESENT topics are families; ordinary is science-domain) — not in frozen readiness |

No V1R9 was created in this CLEAR: inventing a new surface would change the
dataset identity after V1R8 was already trained as experiment 002 and after
Stage-A-003 focal objective was authorized. A further ordinary-source
rebalance would require a **new** named remediation rule, not a silent
re-run of `REMEDIATE_V5_STAGE_A_MIXED_FAILURE_V1`.

## Subsequent scientific state (context)

After V1R8 READY:

1. `HLX-CLASSIFICATION-V5-STAGE-A-002` trained → `SETTLED_FAIL` /
   `RESIDUAL_PRESENT_RECALL_FAILURE`
2. Architecture/objective investigation → H1 focal selected
3. Stage-A-003 focal objective **FROZEN** and train **AUTHORIZED**
   (`AUTHORIZED_V5_STAGE_A_003_FOCAL_LOSS_ONCE`)

## Next action

```text
NEXT_ACTION = TRAIN_V5_STAGE_A_003_FOCAL_LOSS_ONCE
```

Do not re-authorize V1R8. Do not open V1R9 under this CLEAR unless a new
remediation rule is explicitly authorized for ordinary-source rebalance.
