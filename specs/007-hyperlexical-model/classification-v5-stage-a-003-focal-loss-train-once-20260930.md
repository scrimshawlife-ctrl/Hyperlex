# Classification v5 — Stage-A-003 focal-loss train once (`SETTLED_FAIL`)

Experiment: `HLX-CLASSIFICATION-V5-STAGE-A-003-FOCAL-LOSS`  
Surface: V1R8 READY `c0fdd82d…`  
Config: `b8aad3ba…` · focal γ=2.0 · alpha=NONE · seed 42  
SELECTED: `dba6d491…` · restored epoch 12 · run receipt `1ca2e5d4…`

## Preflight

| Check | Result |
|---|---|
| experiment_id | PASS (`HLX-CLASSIFICATION-V5-STAGE-A-003-FOCAL-LOSS`) |
| dataset_sha256 | PASS (`c0fdd82d…`) |
| surface / readiness | PASS (V1R8 / READY) |
| training_config_sha256 | PASS (`b8aad3ba…`) |
| train_authorized | PASS |
| prior Stage-A-003 run count | PASS (0) |
| BEST | PASS (parent `9fba0f66…`) |
| reserve_consumed | PASS (false) |
| OBJECTIVE_STATE | FROZEN |
| SINGLE_FACTOR_DIFF | PASS |

## Focal configuration (from authorization; unchanged)

```text
loss = weighted_focal_cross_entropy
gamma = 2.0
FOCAL_ALPHA_POLICY = NONE
class_weights / provenance multipliers = unchanged from Stage-A-002
FOCAL_LOSS_SPEC_SHA256 = dce6dbf5…
```

## Training

| Field | Value |
|---|---|
| TRAINING_STATUS | COMPLETE |
| PROCESS_EXIT | CLEAN |
| actual_epochs | 12 |
| optimizer_steps | 21324 |
| selected/restored epoch | 12 |
| SELECTED checkpoint SHA | `dba6d491…` |
| FINAL distinct? | no |
| runtime_seconds | 514.8 |

## Threshold selection

```text
THRESHOLD_GRID n_candidates = 45
THRESHOLD_GRID n_passing = 0
chosen = null
feasible = false
fail_if_no_feasible = SETTLED_FAIL
```

Fail-display pair for reported metrics: none=0.50 / present=0.55.

## Stage-A acceptance (frozen)

| Gate | Value | Threshold | Pass |
|---|---:|---:|:---:|
| false_evidence_entry_rate_on_none | 0.008786 | ≤ 0.05 | yes |
| EVIDENCE_PRESENT recall | 0.502355 | ≥ 0.70 | no |
| NO_EVIDENCE recall | 0.988818 | ≥ 0.90 | yes |
| ordinary NONE→PRESENT remains low | 8 | ≤ 22 | yes |
| PRESENT→NONE median P(NONE) < 0.80 | 0.904363 | < 0.80 | no |
| threshold_grid n_passing ≥ 1 | 0 | ≥ 1 | no |

Stage-A macro-F1 (fail-display): **0.509194**

## 3-class P/R/F1 (fail-display)

| Class | P | R | F1 |
|---|---:|---:|---:|
| NO_EVIDENCE | 0.7742 | 0.9888 | 0.8685 |
| EVIDENCE_PRESENT | 0.9581 | 0.5024 | 0.6591 |
| UNCERTAIN | 0.0000 | 0.0000 | 0.0000 |

## Subtype diagnostics (fail-display)

| Subtype | support | NONE recall | false PRESENT |
|---|---:|---:|---:|
| ORDINARY_DOMAIN_NONE | 753 | 0.9867 | 8 |
| HARD_NONE | 143 | 0.9720 | 3 |
| NEAR_DOMAIN_NONE | 148 | 1.0000 | 0 |
| GENERIC_NONE | 53 | 1.0000 | 0 |
| LEXICAL_LOOKALIKE_NONE | 91 | 1.0000 | 0 |
| SHORT_ATOM_NONE | 64 | 1.0000 | 0 |
| POSITIVE_EVIDENCE | 637 | — | — |
| AMBIGUOUS_EVIDENCE | 61 | — | — |

Ordinary NONE→PRESENT: **8** (parent 002: 11; Δ −3). Specificity failure surface
remains low; focal did not reopen ordinary false PRESENT. Val ordinary NONE is
748 OBSERVED / 5 INFERRED, so the residual ordinary FP mass remains on the
OBSERVED ordinary-NONE slice (diagnostic only).

## OBSERVED / INFERRED

| Slice | n | PRESENT R | NONE R | false-entry |
|---|---:|---:|---:|---:|
| OBSERVED | 1503 | 0.4275 | 0.9853 | 0.0116 |
| INFERRED | 447 | 0.9457 | 1.0000 | 0.0000 |

## ATOM / PROSE

| Form | n | PRESENT R | NONE R | false-entry |
|---|---:|---:|---:|---:|
| ATOM | 331 | 0.3130 | 0.9773 | 0.0170 |
| PROSE | 1593 | 0.5453 | 0.9907 | 0.0074 |

## Source / domain cohorts

| Source | n | PRESENT R | NONE R | false-entry |
|---|---:|---:|---:|---:|
| none | 811 | 0.5736 | 0.9919 | 0.0061 |
| wikipedia | 274 | 0.0000 | 1.0000 | 0.0000 |
| wiktionary | 865 | 0.4538 | 0.9794 | 0.0165 |

(`wik` aggregate residual from CLEAR audit remains diagnostic-only; not a frozen
V1R8 readiness gate and did not block this authorized run.)

## vs Stage-A-002 (diagnostic)

| Metric | 002 | 003 focal | Δ |
|---|---:|---:|---:|
| PRESENT recall | 0.527 | 0.502 | −0.025 |
| false-entry | 0.012 | 0.009 | −0.003 |
| ordinary NONE→PRESENT | 11 | 8 | −3 |
| PRESENT→NONE | 297 | 303 | +6 |
| PRESENT→NONE median P(NONE) | 0.994 | 0.904 | −0.090 |
| threshold n_passing | 0 | 0 | 0 |

## Settlement

```text
SCIENTIFIC_RESULT = SETTLED_FAIL
H1_OBJECTIVE_LOSS_PRESSURE = FALSIFIED_FOR_FOCAL_INTERVENTION
PROMOTION_CANDIDATE = false
BEST = UNCHANGED
RESERVE = unused
RESERVE_CONSUMED = false
```

## Retention

Private:
`hlx-private/classification-v5-stage-a-train-v1r8-003-focal-20260930/`
+ `classification-v5-stage-a-003/` (RUN_RECEIPT, SETTLEMENT, THRESHOLD_GRID,
SELECTED, diagnostics). Temporary trainer checkpoints pruned.

Public mirror weights:
`~/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-classification-v5-stage-a-003-focal/`
(`dba6d491…`).

## Next action

```text
NEXT_ACTION = INVESTIGATE_V5_STAGE_A_UNCERTAIN_POLICY
```

Stop. Do not create V1R9, re-remediate V1R8, retune thresholds, start a second
train, consume reserve, mutate BEST, or launch family-head / Stage-B work.
