# Classification v5 — Diagnose V1R1 generalization-retrain SETTLED_FAIL

```text
RULE = DIAGNOSE_V5_STAGE_A_GENERALIZATION_RETRAIN_SETTLED_FAIL
EXPERIMENT = HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-GENERALIZATION-001
FAILED_CHECKPOINT = 26841d5f…
PARENT_DISPOSITION = SETTLED_FAIL
PRIMARY_DIAGNOSIS = GATE1_SEMANTIC_TARGET_MISMATCH
NEXT_ACTION = STAGE_A_SEMANTIC_DECOMPOSITION
STAGE_A_BEST = cd2829c1… UNCHANGED
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
V1R1 = UNCHANGED
V1R2 = NOT_CREATED
TRAIN = false
RESERVE = SPENT / unused
receipt = c6ae58c7…
```

Read-only. No train, V1R2, retune, reserve use, Stage-B mutation, or BEST moves.

## Frozen observed outcome

| Metric | Value |
|---|---:|
| Gate1 macro-F1 | 0.8397 |
| Gate1 NONE / POSSIBLE recall | 0.7845 / 0.9037 |
| Gate1 false-entry | 0.2155 |
| E2E false-entry / PRESENT / NONE | 0.2014 / 0.8907 / 0.7845 |
| SHORT_ATOM NONE false-entry | 0.546 |
| SHORT_ATOM PRESENT recall | 0.750 |
| threshold pairs passing | 0 / 100 |

## Gate-1 error decomposition (@ 0.50)

| Class | n |
|---|---:|
| TRUE_NONE | 444 |
| TRUE_POSSIBLE | 441 |
| FALSE_POSSIBLE | 122 |
| FALSE_NONE | 47 |

**FALSE_POSSIBLE** mass is dominated by ATOM (68%) · length 1–4 (68%) ·
`wiktionary_aggregate` (69%) · subtype `SHORT_ATOM_NONE` (61%) · OBSERVED (82%).

## SHORT_ATOM `p_possible`

| Gold | n | median | p25 | p75 | mean |
|---|---:|---:|---:|---:|---:|
| NONE | 152 | 0.589 | 0.097 | 0.946 | 0.541 |
| PRESENT | 156 | 0.958 | 0.535 | 0.997 | 0.742 |
| UNCERTAIN | 16 | 0.999 | 0.989 | 1.000 | 0.978 |

NONE↔PRESENT histogram intersection **0.629** (heavy overlap). Gate2
`p_confirmed` is near-saturated on both NONE and PRESENT atoms — Gate2 is not
the failure surface.

## Representation

```text
state = SHORT_ATOM_REPRESENTATION_PARTIAL
NONE↔PRESENT centroid cosine = 0.975
mean nearest margin NONE = 0.013
mean nearest margin PRESENT = 0.026
```

Embeddings are only weakly separated; not a clean linear geometry.

## Probes (train-fit / val-eval; diagnostic only; not persisted)

| Probe | overall BA | SHORT_ATOM BA | SA NONE r | SA PRESENT r |
|---|---:|---:|---:|---:|
| A existing Gate1 head | 0.843 | 0.609 | 0.428 | 0.769 |
| B fresh logistic | 0.835 | 0.607 | 0.434 | 0.763 |
| C small MLP | 0.831 | 0.569 | 0.434 | 0.686 |

```text
interpretation = REPRESENTATION_OR_SEMANTIC_FAILURE
```

B does not beat A; C does not beat B. This is not a head-optimization miss.

## Semantic-core (existing gold fields only)

SHORT_ATOM validation mass:

| Class | n |
|---|---:|
| LEXEME_PLUS_RELATION | 179 |
| LEXEME_ONLY | 118 |
| LEXEME_PLUS_CONTEXT | 16 |
| EXPLICIT_EVIDENCE_CORE | 9 |
| NEGATED_OR_NONASSERTED | 2 |

Gate1 is effectively asked to separate **token/domain membership** from
**asserted evidence** without an intermediate supervision signal.

## Provenance / Wiktionary / thresholds / old vs new

- Provenance matched support (same gold/subtype/cell/length/source_family):
  **0 pairs** → `INSUFFICIENT_MATCHED_SUPPORT` (cannot confirm/refute raw
  OBSERVED−INFERRED gap under those controls).
- Wiktionary: `MIXED_SOURCE_EFFECT` (ATOM 1–4 fe 0.597 vs non-wik ATOM 1–4
  0.364; prose gap smaller).
- Threshold class: `STRUCTURAL_CLASS_OVERLAP` — even at Gate1=0.95 with Gate2=0.50,
  false_entry=0.085 while PRESENT still 0.751; no grid point hits all three gates.
- vs STAGE_A_BEST on same V1R1 SHORT_ATOM: centroid cosine essentially unchanged
  (0.973 → 0.975); PRESENT recall ↑ (0.609 → 0.750) and NONE recall ↓
  (0.539 → 0.454). Effect tag:
  `failed_to_improve_representation_separation`.

## Architecture-semantic options (not selected / not trained)

| Option | Addresses | V1R1 support | Risk |
|---|---|---|---|
| A current NO vs POSSIBLE | status quo | yes | high SHORT_ATOM shortcut |
| B assertion gate | lexeme vs assertion | partial | medium |
| C domain then relation | membership vs relation | partial | medium |
| D factorized cores | multi-factor Stage-A | partial | lower if supervised |

## Primary diagnosis / next action

```text
PRIMARY_DIAGNOSIS = GATE1_SEMANTIC_TARGET_MISMATCH
dataset_change_justified = false
objective_change_justified = true
architecture_change_justified = false
semantic_decomposition_justified = true
NEXT_ACTION = STAGE_A_SEMANTIC_DECOMPOSITION
```

Do **not** authorize execution here. Do not create V1R2 yet — another matched-atom
expansion would likely keep sliding the Gate1 boundary without adding the missing
assertion/relation intermediate.

Receipt:
`classification-v5-stage-a-generalization-retrain-diagnose-receipt-20261001.json`
(`c6ae58c7…`).
