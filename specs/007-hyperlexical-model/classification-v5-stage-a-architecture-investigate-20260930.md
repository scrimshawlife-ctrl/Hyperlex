# Classification v5 — Stage-A architecture / objective investigation

```text
MODE = VERIFY → ANALYZE → COMPARE HYPOTHESES → DESIGN MINIMAL TEST → STOP
TRAIN = false
DATASET = V1R8_UNCHANGED
RESERVE = unused
BEST = UNCHANGED
PARENT_EXPERIMENT = HLX-CLASSIFICATION-V5-STAGE-A-002
PRIMARY_DIAGNOSIS = RESIDUAL_PRESENT_RECALL_FAILURE
```

Read-only investigation of SELECTED `b22e9c20…` on READY V1R8 `c0fdd82d…`.
No train, no dataset change, no reserve, no BEST mutation.

## 1. Parent verification

| Check | Result |
|---|---|
| SPECIFICITY_GATE (`false_entry ≤ 0.05`) | **PASS** (`0.012`) |
| PRESENT_RECALL_GATE (`≥ 0.70`) | **FAIL** (`0.527`) |
| NONE recall | PASS (`0.987`) |
| THRESHOLD_GRID_PASSING | **0** / 45 |
| PROMOTION | **FAIL** |
| SCIENTIFIC_RESULT | `SETTLED_FAIL` |

Ordinary NONE→PRESENT remediated `60 → 11`. PRESENT→NONE regressed `146 → 297`
(absolute FN rise partly from larger val PRESENT support `423 → 637`; recall
delta `−0.120`).

## 2. Probability geometry (reconstructed full softmax)

Existing train artifacts store only `evidence_score = P(PRESENT)`. Full
`P(PRESENT)/P(NONE)/P(UNCERTAIN)` recovered by one read-only GPU score of
SELECTED (trunk → BEST frozen base → SELECTED trainable overlay + head).
Confusion exactly matches sealed diagnostic counts.

### PRESENT→NONE (`n=297`) — confidently NONE

| Statistic | Value |
|---|---|
| mean / median `P(PRESENT)` | `0.056` / `0.0015` |
| mean / median `P(NONE)` | `0.813` / `0.994` |
| `P(NONE) ≥ 0.80` and `P(PRESENT) ≤ 0.20` | **0.747** |
| near-boundary band `P(PRESENT)∈[0.45,0.60]` | **0.010** |
| median top1−top2 margin | `0.993` |
| mean entropy | `0.162` |
| top1 | NONE `256` / UNCERTAIN `41` / PRESENT `0` |

**Profile = `CONFIDENT_NONE` (B), not near-boundary (A).**
Threshold-only repair is unsupported.

### Contrasts

| Cohort | n | mean `P(PRESENT)` | note |
|---|---|---|---|
| correct PRESENT | 336 | `0.956` | high-confidence PRESENT |
| ordinary NONE→PRESENT | 11 | `0.927` | residual FP still confident PRESENT |
| correct NONE | 1236 | `0.003` | easy NONE dominate |
| gold UNCERTAIN | 61 | `0.105` | see §4 |

## 3. Hypotheses

### H1 — objective / loss pressure → **SUPPORTED**

After V1R8 negative remediation, weighted CE (NONE clipped at `0.5`, PRESENT
`≈0.87`, UNCERTAIN `≈1.75`; INFERRED×0.5) yields:

- NONE recall `0.987` with near-certain correct NONE
- PRESENT FN deep in NONE (`P(PRESENT)` median `0.0015`)
- class-weighted CE already present; residual is easy-NONE dominance in the
  loss landscape

Focal / margin-aware objectives are scientifically justified; plain further
reweighting alone is less targeted than down-weighting easy NONE. Parent recipe
lists `focal` under `loss.forbidden` — lifting that forbid is the intentional
single factor for the next experiment.

### H2 — hierarchical formulation → **PLAUSIBLE**

`UNCERTAIN` means epistemic ambiguity / unresolved evidence sufficiency, not a
third slang class. Ontology supports:

1. Stage A1: PRESENT vs NOT_PRESENT
2. Stage A2: NONE vs UNCERTAIN given NOT_PRESENT

Softmax retains UNCERTAIN mass (`mean P(UNCERTAIN)=0.590`; top1=UNCERTAIN on
`38/61`), but `decide_evidence` uses **only** `P(PRESENT)` thresholds — so
`38/61` top1-UNCERTAIN rows still decide NONE. Hierarchy is ontology-compatible
for UNCERTAIN, but PRESENT→NONE residuals are confidently NONE, so hierarchy is
not the least invasive next test for the Stage-A gate failure.

### H3 — classification head → **NOT_SUPPORTED**

OBSERVED recipe head: single `Linear(hidden→3)`, CLS pool
`last_hidden_state[:,0]`, no dropout, no extra head layers. Standard and not
unusually restrictive relative to the semantic-overlap failure mode.

### Backbone change → **FALSE**

No evidence that ModernBERT capacity is the binding constraint.

## 4. UNCERTAIN failure (first-class)

Precision `0`, recall `0` under diagnostic thresholds.

| Kind | Finding |
|---|---|
| OBSERVED | Softmax UNCERTAIN mass present; `56/61` → NONE via `P(PRESENT)≤0.50`; `0/61` in band `(0.50,0.55)`; train OBSERVED UNCERTAIN = 2 |
| COMPUTED | `top1=UNCERTAIN ∧ decision≠UNCERTAIN` frac `0.623`; PRESENT FN confident-NONE frac `0.747` |
| INFERRED | Failure is decision-score reduction to `P(PRESENT)` + imbalance / tiny OBSERVED UNCERTAIN support — not missing UNCERTAIN logits |
| NOT_COMPUTABLE | Whether hierarchy alone would clear PRESENT recall ≥ 0.70 |

Do not add UNCERTAIN rows as the next step.

## 5. Selected next experiment (ONE change)

```text
SELECTED_NEXT_HYPOTHESIS = H1_OBJECTIVE_LOSS_PRESSURE
EXPERIMENT_ID = HLX-CLASSIFICATION-V5-STAGE-A-003-FOCAL-LOSS
SELECTED_SINGLE_CHANGE =
  Replace Stage-A loss with class-weighted focal cross-entropy
  (same class weights / provenance multipliers; freeze gamma in recipe;
   no head / hierarchy / backbone / dataset change).
DATASET = V1R8_UNCHANGED
seed / backbone / split / training recipe otherwise held.
```

### Support criterion (pre-registered)

Both frozen Stage-A gates pass (`false_entry ≤ 0.05` AND PRESENT recall ≥ 0.70),
threshold grid `n_passing ≥ 1`, PRESENT→NONE `P(NONE)` median falls below `0.80`,
and ordinary false-PRESENT stays near the remediated low level.

### Falsification criterion (pre-registered)

After one train with only the focal-loss swap: (a) PRESENT recall still `< 0.70`,
OR (b) false-entry `> 0.05` / ordinary false-PRESENT reopens toward parent
levels, OR (c) `n_passing=0` while PRESENT→NONE remain confidently NONE
(`P(NONE)` median still ≥ 0.80).

## 6. Stop

```text
TRAIN = false
NEXT_ACTION = TRAIN_V5_STAGE_A_003_FOCAL_LOSS_ONCE
```

Do not execute the proposed experiment in this investigation turn.
