# Classification v5 — Stage-A-004 architecture / objective investigation (V1R9)

```text
MODE = VERIFY → DECOMPOSE → SEPARABILITY → BOTTLENECK → COMPARE A/B/C → STOP
TRAIN = false
DATASET = V1R9_UNCHANGED
RESERVE = unused
BEST = UNCHANGED
EXPERIMENT = HLX-CLASSIFICATION-V5-STAGE-A-004
PRIMARY_DECISION = STAGE_A_ARCHITECTURE_REDESIGN_REQUIRED
```

Read-only investigation of SELECTED `82840630…` on READY V1R9 `8d4be830…`.
No train, no label/surface change, no reserve, no BEST mutation, no new
experiment loop authorized.

## 1. Frozen baseline

| Check | Result |
|---|---|
| DATA_INTEGRITY | **PASS** (V1R9 `8d4be830…`; parent V1R8 `c0fdd82d…` preserved) |
| LABEL_MAPPING | **PASS** (`HYPERLEX_V5_STAGE_A_GOLD_LABEL_MAPPING_V1`; n_invalid=0) |
| SURFACE_READY | **PASS** |
| SPECIFICITY (`false_entry ≤ 0.05`) | **PASS** (`0.016`) |
| NONE recall (`≥ 0.90`) | **PASS** (`0.983`) |
| PRESENT recall (`≥ 0.70`) | **FAIL** (`0.587`; need ≥72 FN recoveries) |
| THRESHOLD_GRID n_passing | **0** / 45 |
| Focal already falsified (Stage-A-003) | **true** |

## 2. PRESENT FN decomposition (`n=263`)

| Mode | n | % |
|---|---:|---:|
| PRESENT_TO_NONE | 141 | 53.6% |
| REPRESENTATION_FAILURE | 88 | 33.5% |
| LOW_CONFIDENCE | 25 | 9.5% |
| THRESHOLD_FAILURE | 9 | 3.4% |
| PRESENT_TO_UNCERTAIN | 0 | 0% |
| FEATURE_ABSENCE | 0 | 0% |

Profile = **`CONFIDENT_NONE`**. Threshold-only repair unsupported.
Gold-UNCERTAIN remain decision-invisible under `P(PRESENT)`-only policy.

## 3. Representation separability

| Metric | Value |
|---|---|
| PRESENT vs NONE centroid cosine | `0.880` |
| PRESENT FN nearest-NONE frac | `0.335` |
| PRESENT FN nearest-PRESENT frac | `0.376` |
| SEPARABILITY | **`PARTIALLY_SEPARABLE`** |

Not fully collapsed; not cleanly separable. Binding failure is not “bad
surface labels” alone.

## 4. Head / objective bottleneck

```text
BOTTLENECK = MIXED
```

- Linear 3-way CLS head + `decide_evidence(P_PRESENT only)` ignores UNCERTAIN mass.
- Weighted CE NONE clip (`0.5`) + NONE effective mass favors NONE dominance.
- Stage-A-003 focal already falsified easy-NONE downweighting as sufficient.

## 5. Loss-pressure hypothesis (no retrain)

Weighted CE encourages safe NONE conservatism after remediation; softmax couples
PRESENT/NONE so raising PRESENT pressure reopens false-entry. Epistemic
UNCERTAIN is treated as a competing class then discarded at decision time.

## 6. Architecture alternatives (comparison only)

| Option | Complexity | Reversible | Note |
|---|---|---|---|
| A multi-task PRESENT detector | MEDIUM | yes | Shared encoder; family downstream |
| B two-stage decision graph | MEDIUM | yes | NONE vs candidate → UNCERTAIN vs CONFIRMED |
| C current 3-class head | NONE | yes | Status quo; already SETTLED_FAIL |

No winner authorized for training in this step.

## 7. Required decision

```text
PRIMARY_DECISION = STAGE_A_ARCHITECTURE_REDESIGN_REQUIRED
dataset_change_required = false
architecture_change_required = true
new_experiment_required = false
```

## 8. Smallest reversible redesign (spec-only)

```text
change_id = B_TWO_STAGE_DECISION_GRAPH
train_authorized = false
```

Replace flat `decide_evidence(P_PRESENT)` with a reversible two-stage decision
graph on the same encoder: (1) NO_EVIDENCE vs EVIDENCE_CANDIDATE; (2) UNCERTAIN
vs CONFIRMED_PRESENT. Keep V1R9 / BEST / seed frozen until CLEAR.

## Next action

```text
NEXT_ACTION = DESIGN_V5_STAGE_A_ARCHITECTURE_REDESIGN_SPEC
```

Stop. Do not train, remediate V1R9, retune thresholds, consume reserve, promote,
move BEST, or launch another experiment loop in this execution.

Receipt: `classification-v5-stage-a-architecture-investigate-v1r9-receipt-20260930.json`
(`7b16550c…`).
