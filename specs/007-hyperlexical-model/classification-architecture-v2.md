# HYPERLEX_CLASSIFICATION_ARCHITECTURE_V2

**State**: `PREREGISTERED`
**Vocabulary**: `hyperlex.active_families.v1` (19 families)
**Schema**: `hyperlex.classification.v2`
**Contract**: `scripts/shadow/hyperlexical/classification_v2.py`
**Runtime**: `scripts/shadow/hyperlexical/classification_v2_runtime.py`
**Readiness**: `python -m hyperlexical.classification_v2_readiness`

SELECT-006 remains `SETTLED_PASS`. SELECT-007 remains `SETTLED_FAIL`. BEST remains

```text
9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6
```

This document does not move it and does not authorize a training run that fails readiness.

## Journey

The operator asks which active semantic family a span supports. Hyperlex learns that answer. A deterministic policy may abstain. Jev, off by default, may later comment on the result. It does not create the label.

## Workflow

```text
training-split support audit
        ↓
deterministic v1 → v2 row map
        ↓
applicability head + 19-family head + existing unbind heads
        ↓
validation-only temperature calibration
        ↓
deterministic emission
        ↓
optional Jev shadow on operational text only
```

`HYPERLEX_CLASSIFICATION=v2` selects this path inside the existing trainer. Unset stays v1. The v2 path refuses to build an optimizer while any active family has zero training support.

## State transition

```text
DRAFT → PREREGISTERED → READY → RUNNING → SETTLED_PASS | SETTLED_FAIL | SETTLED_INVALID
```

The sealed decisions in this file are `PREREGISTERED`. `READY` is one audit, not a state per missing family. The current training export does not yet have a positive example for every active family, so the run is not `READY` and is not `RUNNING`.

## Contract

### Active family head

The trainable family head is exactly:

```text
gaming-meta
betting-sharp
crypto-degen
internet-slang
memetic
social-status
relationship-dating
approval-disapproval
conflict-aggression
technology-ai
workplace-career
sports-competition
music-entertainment
fashion-aesthetic
regional-cultural
spiritual-mystic
identity-affiliation
politics-civic
ai-native
```

`none`, `ABSTAIN`, and `AMBIGUOUS` are not rows. Legacy names are not rows. These are not renames:

```text
workplace-corp ≠ workplace-career
political-status ≠ politics-civic
brainrot-aura ≠ memetic
kinship-address ≠ relationship-dating
```

An exact source-label match copies that row's weight and bias. Every other active row is exact zero. `nn.Linear` random initialization does not survive. The loader witness records family, source row, mapping status, initialization status, weight hash, and bias hash. Historical checkpoints are not rewritten.

BEST's `id2label` confirms the four exact copies: `betting-sharp`, `crypto-degen`, `ai-native`, `gaming-meta`.

### Provenance weights

```text
OBSERVED non-none applicability = 1.00
OBSERVED non-none family        = 1.00
INFERRED non-none applicability = 0.50
INFERRED non-none family        = 0.50
OBSERVED none applicability     = 1.00
INFERRED none applicability     = 0.25
```

`none` rows have no family loss. Provenance is a multiplier, not a predicted class and not a second cross-entropy. Legacy-lineage rows are excluded from both classify losses. They are not remapped and they are not treated as `NONE`.

### Class weights

Training split only. Reserve, test, held-out, settlement, and measurement rows are rejected.

```text
effective_support(family) = OBSERVED_count + 0.5 * INFERRED_count
```

`effective_support = 0` raises `ACTIVE_FAMILY_WITHOUT_TRAINING_SUPPORT` and lists every such family. The family stays in the head.

Otherwise `M` is the median effective count, `raw = sqrt(M / effective)`, the raw weights are divided by their arithmetic mean, then clipped to `[0.50, 2.00]`. The clip is not renormalized.

Applicability effective counts:

```text
FAMILY_PRESENT = 1.00 * OBSERVED active + 0.50 * INFERRED active
NONE           = 1.00 * OBSERVED none + 0.25 * INFERRED none
```

Class weights are `1/sqrt(effective)`, divided by their mean so the two-class mean is 1. There is no `none` cap and no resampling.

Per row:

```text
applicability_loss = provenance_weight * applicability_class_weight * CE
family_loss        = provenance_weight * family_class_weight * CE
unbind_loss        = existing unbind loss, unchanged
```

### Learned architecture v2.0

```text
ModernBERT encoder
        ├── applicability head     NONE | FAMILY_PRESENT     exact-zero init
        ├── active-family head     19 families               copy or exact zero
        ├── ambiguity interface    loss masked
        └── existing unbind heads
```

No learned ABSTAIN head. No learned ambiguity head. `last_trainable = 2`. Schedule is the SELECT-006 candidate: 12 epochs, minimum 4, patience 4, strict improvement, ties keep the earlier checkpoint, restore best. Learning rate `2e-5`, batch 8, grad accumulation 1, max length 64, strict filler filter, unbind curriculum off, unbind every 1, unbind loss weight 1, unbind primary mixed.

Checkpoint selection, validation only:

```text
selection_score =
    0.50 * active_family_macro_f1
  + 0.25 * applicability_macro_f1
  + 0.25 * observed_active_family_macro_f1
```

Macro-F1 averages labels that have gold support in that split. `OBSERVED` and `INFERRED` stay separate slices.

### ABSTAIN and AMBIGUOUS

ABSTAIN is not trained. After restore-best, validation only:

- Temperature-scale applicability logits. Grid `0.05 .. 5.00` step `0.01`. Lowest NLL wins. Ties prefer the temperature closest to 1, then the lower one.
- Applicability threshold maximizes balanced accuracy of `NONE` versus `FAMILY_PRESENT`. Ties: closest to 0.5, then the lower threshold.
- Temperature-scale family logits on validation rows with active-family gold.
- Family emit threshold: among thresholds that abstain at least one of those rows and keep selective accuracy at least the unfiltered family accuracy, maximize coverage, then selective accuracy, then take the lower threshold. If none qualify, the threshold is 0 and confidence does not abstain. After restore-best the trainer loads that checkpoint, runs this procedure on the ordinary validation split only, and writes `classification-v2-calibration.json`. Training rows and the evaluation reserve are not read.

Emission:

```text
if P(FAMILY_PRESENT) < applicability threshold: ABSTAIN
elif P(FAMILY_PRESENT) <= 0.5:                 NONE
elif max family probability < emit threshold:  ABSTAIN
else:                                          FAMILY(argmax)
```

Argmax ties break toward the earlier vocabulary row. `AMBIGUOUS_EMISSION = DISABLED_PENDING_GOLD`. The result still reports `margin = top1 - top2` and `ambiguous_candidate` when that margin is zero. That flag is not gold and is not a decision.

### Jev

Default `JEV = OFF`. Shadow mode records a provider-neutral `DecisionPacket` and does not change `decision` or `family`. Jev is not a training label, reserve builder, settlement authority, measurement input, `OBSERVED` source, canonical family, or calibration target. Held-out, evaluation reserve, settlement, and measurement surfaces have Jev call count 0. `jevgate-1` does not authorize v2 gating. v2 training does not wait for a provider.

### Evaluation

Report applicability, active-family identification, provenance slices, abstention, and unbind separately. Required numbers include active-family macro-F1, per-family F1 where support exists, applicability macro-F1, `NONE` precision/recall/F1, OBSERVED and INFERRED family macro-F1, coverage, selective accuracy, abstention rate, predicted `NONE` rate, `unbind_clean_exact`, ECE, and a Brier score computed off-packet where it is defined. The packet `brier` stays null. There is no `brier_head`.

The first settled v2 run may be promotion-eligible only under a preregistered acceptance contract. It does not replace BEST by itself.

## Acceptance test

`tests/shadow/test_classification_v2.py` covers the 19-row head, exact copy, zero init, the six provenance weights, the none mask, deterministic class weights, the zero-support blocker, reserve isolation, the selection formula, calibration tie rules, disabled ambiguity emission, Jev off, and shadow non-adoption.

## Implementation task

The contract, heads, loss masks, weights, calibration, selection score, telemetry fields, and readiness audit are in the tree. The trainer calls them only when `HYPERLEX_CLASSIFICATION=v2`. On the current export that path stops before the optimizer because fifteen active families have no positive training support. When support exists, the same path trains, restores the best checkpoint, and freezes the validation calibration artifact.

The next action is one bounded acquisition of positive training examples for every family in the readiness missing-support list. After that audit returns `READY`, run one `TRAIN CLASSIFICATION V2` job. Do not open a micro-experiment series and do not move BEST inside that job.

The morph78 classify train split has no positive row for those fifteen families. Positives that already exist in the identity ledger are `evaluation_reserved` (`EVAL_SPENT` or `EVAL_RESERVE`). They are not training support. Copying them into the export is an isolation failure. `conflict-aggression`, `regional-cultural`, and `spiritual-mystic` have no settled positive in that ledger either. The acquisition has to be new rows, disjoint from reserved identities, for all fifteen families together. Legacy near-matches stay unmapped.

### Training acquisition 2026-09-29

Fresh Wiktionary rows were admitted under the frozen sense-label and definitional-gloss map in `classification_v2_acquire.py`. Evidence seal `8b30c98ad8eac7c136e391103450c9d0d20a3499220e9b48f923eab8218581f1`. MediaWiki supplied each `revision_id`. Jev was off. No evaluation identity was copied. The historical morph78 export is unchanged.

The new export is `/home/morpheus/hlx-private/classification-v2-acquire-20260929/civilian.v0.1.jsonl`, sha256 `aa21415adab0c6ea488c7bdc3ea5495d20126017a094a5df33406f30eccd7e3e`, 9263 rows, 113 fresh OBSERVED rows, 0 fresh INFERRED rows. Fourteen target families have 8 OBSERVED rows. `memetic` has 1 OBSERVED row and remains below the preferred target of 8. Readiness is `READY`. The next action is one `TRAIN CLASSIFICATION V2` run. That run does not move BEST.


