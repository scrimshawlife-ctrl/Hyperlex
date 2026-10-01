# Classification v5 — preserve RESERVE_FAIL + generalization diagnosis

```text
ACTION = PRESERVE_RESERVE_FAIL_AND_DIAGNOSE_V5_GENERALIZATION
RESERVE = HYPERLEX_V5_PROMOTION_RESERVE_001 = SPENT
V5_PROMOTION_RESULT = RESERVE_FAIL
production_promotion = REJECTED
diagnosis = STAGE_A_GENERALIZATION_FAILURE
remediation = NEW_STAGE_A_TRAINING_SURFACE
STAGE_A_BEST = cd2829c1… UNCHANGED
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
Stage-B index = 3fd6c87a… UNCHANGED
thresholds = 0.75 / 0.50 / 0.64 / 0.07 UNCHANGED
receipt = 823c985b…
```

Read-only. No training, recalibration, index rebuild, reserve reuse, or BEST moves.

## Preservation

| Field | Value |
|---|---|
| V5_PROMOTION_RESERVE_001 | SPENT |
| V5_PROMOTION_RESULT | RESERVE_FAIL |
| production_promotion | REJECTED |
| evaluation_spent | true |
| reuse as train/val/cal/index | false |

Reserve hashes, identities, decisions, and wrong-emission evidence remain unchanged.

## Stage-A validation → reserve

| Metric | Validation | Reserve | Δ |
|---|---:|---:|---:|
| false_entry | 0.0423 | 0.0984 | +0.0560 |
| PRESENT recall | 0.7049 | 0.3711 | −0.3338 |
| NONE recall | 0.9089 | 0.5738 | −0.3352 |
| UNCERTAIN recall | 0.6790 | 0.6000 | −0.0790 |

### Dominant failure cohorts

- **false_entry:** ATOM / hub_or_surface NONE (esp. SHORT_ATOM / short 3–5 tokens); OBSERVED NONE also contributes.
- **PRESENT miss:** Wiktionary-acquire PROSE positives blocked or Gate2-rejected; hub ATOM positives heavily Gate2-rejected.
- **NONE→UNCERTAIN leak:** HARD_NONE and GENERIC_NONE ATOM hub rows.

## Gate routing (reserve)

| Gold | Route | n |
|---|---|---:|
| PRESENT | CORRECT_PRESENT | 59 |
| PRESENT | PASSED_GATE1_REJECTED_GATE2 | 66 |
| PRESENT | BLOCKED_AT_GATE1 | 34 |
| NONE | CORRECT_NONE | 35 |
| NONE | LEAKED_GATE1_TO_UNCERTAIN | 20 |
| NONE | LEAKED_GATE1_TO_PRESENT | 6 |
| UNCERTAIN | CORRECT_UNCERTAIN | 18 |
| UNCERTAIN | PROMOTED_PRESENT | 9 |
| UNCERTAIN | BLOCKED_AS_NONE | 3 |

## Representation

Preregistered nearest-train cosine rule: IN≥0.78 / NEAR≥0.62 / else OOD.

| Split | IN | NEAR | OOD |
|---|---:|---:|---:|
| validation | 1913 | 127 | 11 |
| reserve | 170 | 78 | 2 |

Reserve is mostly in/near distribution. Failure is not primarily embedding OOD; it is Stage-A decision-boundary / surface mismatch on ATOM hub NONE and Wiktionary PRESENT prose.

## Stage-B (correct Stage-A PRESENT only)

| Metric | Val correct-PRESENT | Reserve correct-PRESENT |
|---|---:|---:|
| n | 449 | 59 |
| emission precision | 0.854 | 0.909 |
| coverage | 0.198 | 0.186 |
| top1 / top2 | 0.439 / 0.535 | 0.407 / 0.559 |

Pure Stage-B family failures among FAMILY emissions: **1**. Stage-A-induced FAMILY failures: **4**.

## Wrong emissions (5)

| Class | n |
|---|---:|
| STAGE_A_FALSE_ENTRY | 1 |
| STAGE_B_WRONG_FAMILY | 1 |
| STAGE_A_AND_B_COMPOUND | 3 |

## Diagnosis

```text
STAGE_A_GENERALIZATION_FAILURE
```

Smallest remediation:

```text
NEW_STAGE_A_TRAINING_SURFACE
```

Dataset change justified: yes (Stage-A surface). Architecture change: no. Stage-B index change: not justified as primary (Stage-B holds when Stage A admits correctly).

## Next action

```text
NEW_STAGE_A_TRAINING_SURFACE — do not retune 0.75/0.50 or 0.64/0.07;
do not train on reserve mistakes; do not add reserve identities to the index.
```

Private artifacts: `/home/morpheus/hlx-private/classification-v5-reserve-fail-diagnose-20261001/`.
