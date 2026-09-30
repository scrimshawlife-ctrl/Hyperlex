# Classification v5 — Stage-A train once (`TRAIN_V5_STAGE_A_ONCE`)

```text
EXPERIMENT_ID = HLX-CLASSIFICATION-V5-STAGE-A-001
TRAINING_STATUS = COMPLETE
SCIENTIFIC_DISPOSITION = SETTLED_FAIL
PROMOTION_CANDIDATE = false
BEST_MUTATED = FALSE
RESERVE_CONSUMED = FALSE
```

## Pins

| Pin | Value |
|---|---|
| dataset | `a81ca68ad3310981c60d2500a83a0989adeb967cbee6ad6dff003ed2c705efa9` |
| training config | `4d2eaabd52976da6beecfac1175770a9f3402c82d0b124942638488aa8ab4d7e` |
| code revision (sealed auth) | `1b0264a6ee484068dbd1b284e8d2ff22789a245b` |
| parent BEST | `9fba0f66…` UNCHANGED |
| seed | `42` |
| restored epoch | `6` |
| actual epochs | `10` |
| optimizer steps | `18180` |
| SELECTED checkpoint SHA256 | `3b1b574acceea183363b8cea41e1b7e4e13dc934bacc66deb4b3b8caeabc90a7` |
| run receipt SHA256 | `b429990532ff84aa3eb9fb43ef0ef5b83a633e6a9441efb6807bd6a0c7b02c98` |

## Settlement

Authorized threshold grid: 45 candidates, **0 passing**. No pair satisfied all
three frozen gates → **`SETTLED_FAIL`**. Gates were not loosened.

| Gate | Value | Threshold | Pass |
|---|---|---|---|
| false_evidence_entry_rate_on_none | `0.06915` | ≤ 0.05 | FAIL |
| EVIDENCE_PRESENT recall | `0.6478` | ≥ 0.70 | FAIL |
| NO_EVIDENCE recall | `0.9286` | ≥ 0.90 | PASS |

(Fallback display thresholds `0.50/0.55` used only because the grid had no
feasible pair; they are not selected operating thresholds.)

## Retention

```text
INITIAL   = BEST + deterministic head init (manifest; reconstructible)
SELECTED  = epoch 6 loadable weights (permanent failed scientific evidence)
FINAL     = epoch 10 retained (differs from SELECTED)
tmp_checkpoints pruned after settlement
optimizer/scheduler state not retained after settlement
```

Private root:
`hlx-private/classification-v5-stage-a-train-20260930/classification-v5-stage-a-001/`

## Dominant failure structure (diagnostic)

- `ORDINARY_DOMAIN_NONE`: false PRESENT rate `0.176` (60/341)
- `OBSERVED` worse than `INFERRED` (false-entry `0.134` vs `0.002`)
- `wiktionary` source false-entry `0.235`
- ATOM↔NONE / PROSE↔PRESENT pure-form shortcut is **not** the dominant error
  pattern (errors mixed; ATOM share of errors ≈ 0.45)

## Exact next action

```text
DIAGNOSE_V5_STAGE_A_SETTLED_FAIL
```

No second train. No reserve. No BEST move. No family-head work.
