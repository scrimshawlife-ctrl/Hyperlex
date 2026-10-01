# Classification v5 — Stage-A V1R9 train authorization

`AUTHORIZE_V5_STAGE_A_NEXT_RUN_ON_REMEDIATED_SURFACE` for experiment
`HLX-CLASSIFICATION-V5-STAGE-A-004`.

| Pin | Value |
|---|---|
| Surface | `HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R9` |
| Dataset | `8d4be830…` |
| Readiness receipt | `0b551c76…` |
| Gate eval | `ff9cc665…` |
| Resolved config | `0c9df174…` |
| Authorization receipt | `7657092a…` |
| BEST | `9fba0f66…` UNCHANGED |
| Parent diagnosis | `MIXED_UNCERTAIN_SURFACE_FAILURE` |
| Parent surface | V1R8 `c0fdd82d…` preserved |

Sealed GATE_EVAL / READINESS digests on the READY V1R9 surface (metadata
only; dataset body unchanged). Freezes weighted cross-entropy Stage-A
recipe. Does not train. Does not consume reserve. Does not move BEST.

Isolated private auth dir:
`hlx-private/classification-v5-stage-a-train-v1r9-20260930/`.

Public receipt:
`classification-v5-stage-a-train-v1r9-authorize-receipt-20260930.json`.

Next: `TRAIN_V5_STAGE_A_ONCE` (exactly one run).
