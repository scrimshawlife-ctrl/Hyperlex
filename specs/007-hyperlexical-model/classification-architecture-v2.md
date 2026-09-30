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

The new export is `/home/morpheus/hlx-private/classification-v2-acquire-20260929/civilian.v0.1.jsonl`, sha256 `aa21415adab0c6ea488c7bdc3ea5495d20126017a094a5df33406f30eccd7e3e`, 9263 rows, 113 fresh OBSERVED rows, 0 fresh INFERRED rows. Fourteen target families have 8 OBSERVED rows. `memetic` has 1 OBSERVED row and remains below the preferred target of 8. Readiness is `READY`. The training run does not move BEST.

### Training run 2026-09-29

One `HYPERLEX_CLASSIFICATION=v2` run used that export, the SELECT-006 candidate schedule, `last_trainable` 2, and a warm start from the production checkpoint. Jev stayed off. The run restored the best checkpoint by `selection_score` and wrote `classification-v2-calibration.json` from the validation split only. Output is `/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-classification-v2`, primary weights sha256 `405107de9b9ca580fc578f47314d3a18490e598c56c988cfc5f8ac53409cecea`. BEST remains the select004 checkpoint, sha256 `9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6`.

Early stopping ended the run after 7 epochs. The best epoch is 2, validation `selection_score` 0.8077923974493622. Applicability temperature 1.83, applicability threshold 0.7803025403596302, family temperature 1.19, family emit threshold 0.07590847237608982. Calibration used no reserve rows and no training rows.

No comparison hypothesis was preregistered, so the run is not `SETTLED_PASS` or `SETTLED_FAIL`. Execution matched the contract, so it is not `SETTLED_INVALID`. Promotion is a later explicit action.

The frozen classify `EVAL_RESERVE` is 115 identities. Their stored strings were scored once with the restored checkpoint and the validation calibration. Seventy-five are OBSERVED headwords. Forty are INFERRED `none` sentences. None of those strings are in the training export. The ledger was not changed. SELECT-006 and SELECT-007 were not reopened.

On that pass, applicability macro-F1 is 0.5656, `NONE` F1 is 0.320, and active-family macro-F1 is 0.1360 where gold support exists. Coverage is 0.8348, selective accuracy is 0.1875, and the abstention rate is 0.1652. The applicability threshold sits above 0.5, so the decision `NONE` branch did not fire. Applicability Brier is 0.2062 and 10-bin ECE is 0.1976. Packet `brier` stays null. `unbind_clean_exact` is null on this classify reserve. The receipt is `/home/morpheus/hlx-private/classification-v2-train-20260929/RESERVE_EVAL.json`.


### Sense-text continuation

The first run stored the Wiktionary page title in `text` while the family decision came from one tagged sense. Short titles such as `fruit` and `iron` then trained as if the whole headword were that family. Validation gold for the fifteen new families was zero, so checkpoint selection could not see those emissions.

The evidence map is unchanged. Where `definition_prose` is stored and its identity is disjoint from the historical export and from the evaluation reserve, the training string is that prose. Empty prose, and one prose string that duplicated another fresh row, keep the page title. Twenty-seven prose rows, chosen by sorting `normalized_text_sha256` and holding out two when a family has at least four prose rows or one when it has two or three, are `split=val`. Title fallbacks stay in train. `memetic` has a single prose row, so it stays in train. The run uses the same schedule, warm start, and loss. It does not move BEST and it does not score the evaluation reserve.


The sense-text run finished under the same schedule. Output is `/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-classification-v2-sense`, primary weights sha256 `940055e846ecf525e5fa3a57293accd550cf84d739e3d9046f0f6c7d824e6701`. Early stopping restored epoch 2. Validation `selection_score` is 0.3741016490791826. Applicability macro-F1 is 0.9279. Active-family macro-F1 is 0.1967 because fourteen new families now have validation gold and thirteen of them score 0. `conflict-aggression` F1 is 0.4 on two rows. The four original families stay at ai-native 0.8655, betting-sharp 0.7407, crypto-degen 0.7907, and gaming-meta 0.7429. Calibration on validation only: applicability temperature 1.42, applicability threshold 0.5437899749549117, family temperature 1.15, family emit threshold 0.07211037498260023. BEST is unchanged. The evaluation reserve was not scored again.


### Semantic prototype initialization

New active-family rows are no longer exact zero. An exact-name row in the warm-start classifier is copied, weight and bias. Every other active family is initialized from the frozen warm-start encoder, before any v2 update: the first-token representation of each training-split definition, weighted OBSERVED 1.0 and INFERRED 0.5, L2-normalized, then multiplied by the median L2 norm of the copied rows. Bias is 0. Page titles are not prototype sources when a definition is stored. Jev is off. The witness is `7faa98239b2d4f39bf722c776543ded9a6c5959646c09c5db1e977cd7e69855d`. Two builds matched. The target norm is 1.1618999419668148, from the four copied rows `gaming-meta`, `betting-sharp`, `crypto-degen`, and `ai-native`. The warm start overlay loaded 48 encoder tensors. Pooling is `last_hidden_state[:, 0]`, max length 64.

Readiness on the sense-text export is not READY. The only blocker is `VALIDATION_FAMILY_SUPPORT_INSUFFICIENT`: `internet-slang` has 1 validation positive and `memetic` has 0. Every other active family has at least 2. Thirteen new families are below the preferred support of 4. Definition strings, prototypes, copied rows, family weights, applicability weights, isolation, and the selection formula passed. BEST was not moved. The evaluation reserve was not scored. Training did not start.

### Validation admission for internet-slang and memetic

The sense-text export stayed in place. Its sha256 is still `a1332bce1dcf8a3e2646243990e1c9104e191019dae9324ffb9bbce91a28c1cc`. A new export, `/home/morpheus/hlx-private/classification-v2-validation-20260929/civilian.v0.2.jsonl`, sha256 `595440b53664b1c9433b5d535cd59778c62b0cf932df0c5a1b434003c211effa`, keeps that prefix and appends 59 validation definitions: 57 `internet-slang` and 2 `memetic` (`iceberg chart`, `wunkus`). Validation support is `internet-slang` 58 and `memetic` 2. The new identities are catalogued and are not training-consumed or evaluation-reserve. Training rows, family weights, applicability weights, and prototype witness `7faa98239b2d4f39bf722c776543ded9a6c5959646c09c5db1e977cd7e69855d` are unchanged. Readiness on this export is READY. BEST was not moved. Training did not start.

### Ready training run

Training used the validation export `595440b53664b1c9433b5d535cd59778c62b0cf932df0c5a1b434003c211effa` and prototype witness `7faa98239b2d4f39bf722c776543ded9a6c5959646c09c5db1e977cd7e69855d`. The schedule ran all 12 epochs. Epoch 8 had the best validation `selection_score`, 0.4254809855319254. Applicability macro-F1 is 0.9413. Active-family macro-F1 is 0.2540. Observed active-family macro-F1 is 0.2527. Output is `/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-classification-v2-ready`, primary weights sha256 `a8d50a4dcb4d886b3a5daae5740abaae9390595fdbee007da7b0c0372571b4b9`. The trainer restored that checkpoint and then hit `math domain error` in calibration NLL, where `log` of an underflowed class probability is undefined. Log-sum-exp now computes the same NLL and stays finite. Calibration on the saved checkpoint, validation only: applicability temperature 1.05, applicability threshold 0.6043058422230875, family temperature 5.0, family emit threshold 0.0877033765576476, 548 applicability rows and 254 family rows. Family temperature is the top of the sealed 0.05–5.00 grid. BEST is unchanged. The evaluation reserve was not scored. Training did not promote the checkpoint.

### Corrected calibration and reserve evaluation

The temperatures in the ready-run paragraph describe a post-hoc reload that applied the 12 trained encoder tensors and omitted the production select004 overlay of 48 encoder tensors. That file remains `classification-v2-calibration.trunk-only.json`. Its applicability temperature is 1.05, its applicability threshold is 0.6043058422230875, its family temperature is 5.0, and its family emit threshold is 0.0877033765576476. Family temperature 5.0 is the top of the sealed grid for that discarded reload.

The canonical file `classification-v2-calibration.json` reloads the production encoder, 48 tensors, and then the ready checkpoint encoder, 12 tensors, followed by the ready applicability and family heads. The grid, tie breaks, and validation-only surface are unchanged. Applicability temperature is 1.98. Applicability threshold is 0.5211848104881056. Family temperature is 3.45, inside the sealed 0.05–5.00 grid. Family emit threshold is 0.09918229139032707. The fit used 548 applicability rows and 254 family rows. Checkpoint identity remains `a8d50a4dcb4d886b3a5daae5740abaae9390595fdbee007da7b0c0372571b4b9`. BEST remains the select004 checkpoint.

The frozen classify evaluation reserve, 115 identities, was scored once with that stack. Applicability macro-F1 is 0.4780. Active-family macro-F1 is 0.1495. Observed active-family macro-F1 is the same 0.1495. Coverage is 0.7391. Selective accuracy is 0.2118 on 85 emitted rows. The abstention rate is 0.2609. The applicability head predicted NONE on 0.2435 of the rows. The decision NONE branch did not fire, so `none_decision_rate` is 0. Applicability Brier is 0.3746 and 10-bin ECE is 0.3929. The receipt is `/home/morpheus/hlx-private/classification-v2-train-ready-20260929/RESERVE_EVAL.json`. The ledger was left as it stood after validation admission. The score did not select a checkpoint and did not move BEST.

Against the first v2 reserve score of checkpoint `405107de9b9ca580fc578f47314d3a18490e598c56c988cfc5f8ac53409cecea`, selective accuracy is 0.2118 where that score was 0.1875, and active-family macro-F1 is 0.1495 where that score was 0.1360. Applicability macro-F1 is 0.4780 where that score was 0.5656. Coverage is 0.7391 where that score was 0.8348. Promotion remains a later explicit action.

### Promotion decision

The ready checkpoint is not promoted. BEST stays the select004 weights, sha256 `9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6`. This run has no preregistered acceptance contract.

On the 115 reserve identities, both this checkpoint and the first v2 checkpoint `405107de9b9ca580fc578f47314d3a18490e598c56c988cfc5f8ac53409cecea` place the gold family on 18 rows. The four gains are gaming-meta `equip` and `mise`, betting-sharp `pick 'em`, and crypto-degen `stake`. The four losses are ai-native `neuroid`, betting-sharp `flat` and `short`, and crypto-degen `side chain`. The other reserve families stay at zero hits.

Applicability on this reserve does not separate the classes. The correlation of calibrated P(FAMILY_PRESENT) with gold family-present is -0.067. The correlation of word count with gold family-present is -0.884. Sixty-nine of the one- and two-word rows are family atoms, and all 40 none rows are longer sentences. Mean P(FAMILY_PRESENT) is 0.707 on those short atoms and 0.829 on the sentences of 13 words or more. In the training export, none text is a short headword, median 1 word, and fresh family text is definition prose. Reserve none text is an encyclopedic sentence, median 15 words. Validation applicability macro-F1 0.9413 measures the export surface, where both classes are short Wiktionary strings.

The next training variable is that surface. Encyclopedic none sentences and short family atoms are not in the current export as a pair, so another definition harvest would not test this gap. No such run is started here.

### Applicability surface balance

The ready checkpoint showed an applicability shortcut: training NONE rows are short headwords and fresh family rows are definition prose, while the reserve is the inverse. Validation applicability macro-F1 0.9413 stays a property of that export surface. The preregistered guard, chosen before the surface-balanced run, is `abs(corr(word_count, P(FAMILY_PRESENT))) <= 0.30` on the validation split after calibration. The reserve is not a fitting surface for that correlation.

Surface form is structural. ATOM is one to four whitespace tokens with no sentence terminator and no comma or semicolon. PROSE is six or more tokens, or any sentence terminator, or a comma or semicolon. Five-token strings with neither are AMBIGUOUS and are masked out of the applicability objective. The family label is not an input. Rule id `hyperlex.classification.v2.surface.v1`.

Applicability loss gives each populated cell equal aggregate authority: cell weight is `1 / effective_cell_support`, then the populated cell weights are scaled to mean 1. Provenance authority is applied inside the cell. Family class weights keep the existing formula. Prototype initialization, calibration, schedule, ontology, and BEST are unchanged. Jev stays off.

### Applicability shortcut diagnostic correction

The surface-balanced run stays failed under the guard that was preregistered before it. On the validation split after calibration, `abs(corr(word_count, P(FAMILY_PRESENT)))` is 0.42150272051315185. The limit was 0.30. `SETTLEMENT.json` still records `shortcut_pass` false for checkpoint `e3c0545424e7fe9ca93a9b8c5e423698974f5cecab405ed99590c8293a5bb463`. That settlement was not rewritten. The evaluation reserve was not scored. BEST remains select004, sha256 `9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6`.

The global correlation mixes the gold applicability class with length. Longer positive definitions carry more evidence than short positive atoms. The same validation replay, temperature 1.47, production encoder overlay of 48 tensors then the surface encoder overlay of 12 tensors, reproduces the stored cell means with delta 0:

```text
FAMILY_PRESENT/ATOM   mean P = 0.7852956405720147   F1 = 0.8453608247422681
FAMILY_PRESENT/PROSE  mean P = 0.911294776451496    F1 = 0.9776119402985074
NONE/ATOM             mean P = 0.1279144847425886   F1 = 0.918918918918919
NONE/PROSE            mean P = 0.12663721872007336  F1 = 0.90625
```

The corrected diagnostic is read-only. Rule id `hyperlex.classification.v2.surface_invariance.v1`. It does not enter the loss, and it does not change the encoder, either head, the prototype witness, the family weights, the surface weights, the schedule, or calibration. Conditional correlations do not pool the two gold classes:

```text
corr(word_count, P | FAMILY_PRESENT) = 0.24186883570934187   n = 296
corr(word_count, P | NONE)            = 0.13799315805567047   n = 302
FAMILY_PRESENT/ATOM                   = -0.015312949853750339 n = 155
FAMILY_PRESENT/PROSE                  = 0.27285157444473607   n = 135
NONE/ATOM                             = 0.05213599221711015   n = 268
NONE/PROSE                            = 0.5504937075122819    n = 31
```

The preferred scalar fits `P(FAMILY_PRESENT) ~ gold_applicability + surface_class` by ordinary least squares on these 598 validation rows, then correlates the residual with word count. The design columns are intercept, gold FAMILY_PRESENT, surface PROSE, and surface AMBIGUOUS. `corr(residual, word_count)` is 0.09290446228999852.

```text
family_surface_gap = 0.1259991358794813
none_surface_gap   = -0.0012772660225152388
```

The corrected guards, chosen before this replay and not taken from the evaluation reserve, are `abs(none_surface_gap) <= 0.10`, `abs(residualized_length_correlation) <= 0.30`, and FAMILY_PRESENT F1 and NONE F1 at least 0.80 on both populated surfaces. All three pass. The family surface gap is reported and is not a guard. Family atoms and family prose are not required to have the same confidence.

For architecture diagnosis, `APPLICABILITY_SURFACE_SHORTCUT` is `RESOLVED`. That status does not promote the checkpoint and does not turn the historical run into a pass. The receipt is `/home/morpheus/hlx-private/classification-v2-train-surface-20260929/INVARIANCE_DIAGNOSTIC.json`.

The active-family head stays a separate unresolved issue. Active-family macro-F1 is 0.1960828268105939. ATOM family macro-F1 is 0.226814225201322. PROSE family macro-F1 is 0.2664313342411146. The next substantive target is `ACTIVE_FAMILY_DISCRIMINATION`.

The within-NONE/PROSE length correlation, 0.5504937075122819 on 31 rows, is recorded and is not one of the frozen guards. The NONE mean does not move with surface form, and the residualized length correlation stays inside 0.30.

### Prototype-aware family discriminator

Applicability stays closed. The open failure is active-family discrimination. The surface checkpoint's active-family macro-F1 is 0.1960828268105939, ATOM family macro-F1 is 0.226814225201322, and PROSE family macro-F1 is 0.2664313342411146. A pure 19-way linear head has to learn each sparse boundary on its own. The family head now scores a frozen semantic prototype and a learned residual together.

For a normalized encoder vector `h` and a normalized frozen prototype `p_f`:

```text
s_f = cosine(h, p_f)
r_f = residual linear logit on h
z_proto = population_zscore(s / tau)
z_resid = population_zscore(r)
z_f = z_proto + z_resid
```

`alpha` and `beta` are the shared constants 1. Population z-score is across the 19 families of one example. A constant component becomes the zero vector, so a global magnitude cannot dominate. `tau` is 0.10. Dividing by that positive constant does not change the z-score; `tau` is the contrastive temperature. The canonical family decision is `argmax(z_f)`.

The contrastive term, on family-positive rows only, is temperature-scaled prototype NLL. The gold denominator weight is 1. The top 3 other prototypes for that gold family, taken from the frozen prototype-to-prototype matrix, use weight 2. Every other family stays at 1. `lambda_proto` is 0.5. Provenance and family class weights multiply this term the same way they multiply the family cross-entropy. Prototypes are buffers. They are not updated and they are not recomputed each epoch.

The fifteen verified semantic prototypes are copied from witness `7faa98239b2d4f39bf722c776543ded9a6c5959646c09c5db1e977cd7e69855d`. The four exact-copy families now also have semantic prototypes, built from their training prose with the frozen production encoder. Residual rows for those four families still initialize from the exact checkpoint rows. The other residual rows start at zero. The geometry witness is `/home/morpheus/hlx-private/classification-v2-geometry-20260930/PROTOTYPE_GEOMETRY.json`, prototype witness sha256 `d9ab8780dc000cc3e2b277e0c68720cbc5d7a513dfc02683414bf64a0384214a`, geometry sha256 `8392da2b05a256adea98dac39503ad05c948ac9f2bd7b04883bee56019c7e390`.

Prototype cosine at or above 0.80 marks a confusable pair. There are 89 such pairs. They form one cluster of the fifteen definition-initialized families plus `ai-native`. `betting-sharp`, `crypto-degen`, and `gaming-meta` stay outside that threshold. Families are not merged.

On the current validation split, before this training run, prototype-only macro-F1 is 0.13964619279491827, residual-only macro-F1 is 0.1960828268105939, and fused macro-F1 is 0.1725259920541627. The residual-only figure matches the surface checkpoint. The reserve was not scored. BEST is unchanged.

The geometry training run is `HLX-CLASSIFICATION-V2-GEOMETRY-20260930`. Schedule, optimizer, applicability head, provenance weights, family class weights, encoder depth, calibration, unbind, and the selection score were unchanged. Jev stayed off. The restored checkpoint is epoch 8 of 12, primary weights `ce0db72c610df3b1a5be5736e2ea80620dacdf5cc30ac5903709590dfc99a411`. Selection score on that epoch is 0.3538945986627647.

Active-family macro-F1 is 0.18150134757636427. That is below the surface checkpoint's 0.1960828268105939, so the internal gate does not open. ATOM family macro-F1 is 0.22790560869049023. PROSE family macro-F1 is 0.2210162379713775. Macro-F1 over the fifteen non-exact-copy families is 0.041352657004830914. Seven of nineteen families have F1 above 0, six have F1 at or above 0.20, and four have F1 at or above 0.50. Three of those nonzero families are outside the exact-copy set: fashion-aesthetic 0.2, identity-affiliation 0.08695652173913042, and spiritual-mystic 0.3333333333333333. The other twelve new families, including internet-slang, have F1 0.

Applicability invariance still passes. `none_surface_gap` is -0.03337497558181346. Residualized length correlation is 0.08658422091556929. FAMILY_PRESENT F1 is 0.8589341692789969 on ATOM and 0.9739776951672863 on PROSE. NONE F1 is 0.9146110056925996 on ATOM and 0.8888888888888888 on PROSE. Architecture validation is `INTERNAL_SHORT`, not `SETTLED_INVALID`. The reserve was not scored. Reserve scoring is not justified. BEST remains `9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6`.

The frozen prototypes did not separate the sparse families. Eighty-nine prototype pairs sit at cosine 0.80 or above, in one cluster of the fifteen definition-initialized families plus `ai-native`. That collinearity is the remaining bottleneck. No further training run, loss-weight change, or reserve score follows from this result.

### Multi-anchor family boundaries

`HYPERLEX_FAMILY_SEMANTIC_BOUNDARIES_V1` replaces the single family centroid as the canonical semantic representation. This pass does not train, does not score the reserve, and does not move BEST. BEST remains `9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6`.

Anchor count is support first, then the smallest separated clustering. For `n` training-positive definitions: `n <= 2` gives `k = 1` and `support_status = SPARSE`; `3 <= n <= 5` gives `k = 2`; `6 <= n <= 11` gives `k_max = 3`; `12 <= n <= 23` gives `k_max = 4`; larger `n` gives `k_max = 5`. When `k_max` is set, the search tries `k` from 2 through `k_max` and keeps the smallest `k` whose mean cosine silhouette is at least 0.20 and whose every cluster has support at least 2. If none qualify, `k = 2`. Clustering is farthest-first spherical k-means in cosine distance, `random_seed = 0`, at most 32 iterations, ties broken by the lowest source identity hash. An anchor is the normalized provenance-weighted mean of its cluster, with OBSERVED weight 1.0 and INFERRED weight 0.5. `n = 3` still uses `k = 2`, so one anchor may have support 1. That case is not SPARSE.

Sources are training-split classification rows only (`classify` or `classify+unbind`). Families with stored definition prose use that prose. Exact-copy families use their training prose. Validation, the test split, EVAL_RESERVE, EVAL_SPENT, EVAL_BOUND, held-out rows, measurement surfaces, and Jev output are excluded. Jev is OFF. No synthetic anchors are added.

The sealed artifact is `/home/morpheus/hlx-private/classification-v2-boundaries-20260930/FAMILY_SEMANTIC_BOUNDARIES.json`. Anchor witness sha256 `369dfb0066e5f2332d8eea927def2a622551fd0c721ece17f75bd263ed67a7e3`. Separation matrix sha256 `ab698d342d2d276f81d4baf3fed609bb6f8bf88cd6810bb1d1998c5e409f63c3`. Boundary sha256 `0ca6f34ce1abf68388e443371672ca36e16028079a175b6775e1968900e1c52f`. Encoder overlay loaded 48 tensors. Excluded reserved identities: 0.

Anchor counts: gaming-meta 2 (n=81), betting-sharp 1 SPARSE (n=2), crypto-degen 2 (n=29), internet-slang 1 SPARSE (n=1), memetic 1 SPARSE (n=1), social-status 2 (n=6), relationship-dating 2 (n=6), approval-disapproval 2 (n=6), conflict-aggression 2 (n=6), technology-ai 2 (n=6), workplace-career 2 (n=5), sports-competition 2 (n=6), music-entertainment 2 (n=5), fashion-aesthetic 2 (n=6), regional-cultural 2 (n=3, supports 2 and 1), spiritual-mystic 2 (n=6), identity-affiliation 2 (n=4), politics-civic 2 (n=6), ai-native 2 (n=503). Sparse families are betting-sharp, internet-slang, and memetic. Every non-sparse family stopped at two anchors. ai-native's two-anchor silhouette is 0.8195, so the smallest-k rule does not open a third anchor. approval-disapproval and conflict-aggression missed the 0.20 silhouette floor at both k=2 and k=3 and therefore use the fallback `k = 2`.

There are 284 anchor pairs at cosine 0.80 or above: 272 across families and 12 inside a family. The closest cross-family pairs are relationship-dating/music-entertainment 0.9937, social-status/approval-disapproval 0.9897, and social-status/music-entertainment 0.9894. Families are not merged.

The future scorer, specified and not fit, is `population_zscore(max anchor cosine) + population_zscore(residual logit)`. Hard negatives are the nearest competing anchors, three of them, at multiplier 2.0. The mean family centroid is not the semantic score.

### Encoder geometry repair

`HYPERLEX_FAMILY_GEOMETRY_REPAIR_V1` trains the existing last two encoder layers against the sealed multi-anchor boundaries. The ontology, applicability head, schedule, provenance weights, calibration, unbind path, and BEST stay put. Jev stays off. This is not a SELECT experiment.

Canonical family logits are the learned residual head only. Frozen prototype cosine is not fused into the decision. The sealed boundary anchors structure a supervised contrastive geometry loss on family-positive rows:

```text
L_geometry =
- log(
    sum_{a in anchors(f)} exp(cos(h, a) / tau)
    /
    sum_{a in all anchors} m(a) * exp(cos(h, a) / tau)
  )
L_total = existing v2 loss + lambda_geometry * L_geometry
```

`tau = 0.10`. `lambda_geometry = 0.5`. `m(a) = 2.0` when `a` belongs to one of the three nearest competing families from `FAMILY_SEMANTIC_BOUNDARIES_V1`, otherwise `1.0`. Hard negatives are not recomputed from validation or reserve predictions. Sparse families `betting-sharp`, `internet-slang`, and `memetic` keep their single sealed anchor as the positive reference and remain in the 19-way objective.

Residual rows still initialize from exact-copy select004 rows where available; every other residual row starts at zero. `last_trainable` remains 2. Boundary artifact sha256 `0ca6f34ce1abf68388e443371672ca36e16028079a175b6775e1968900e1c52f`. Separation sha256 `ab698d342d2d276f81d4baf3fed609bb6f8bf88cd6810bb1d1998c5e409f63c3`.

Internal gates before any reserve score: active-family macro-F1 above 0.1960828268105939, non-exact-copy family macro-F1 above 0.041352657004830914, more than three non-exact-copy families with F1 above 0, median gold-versus-nearest-negative margin above the pre-training median on the same validation rows, fewer high-collision validation rows than the pre-training count, and applicability invariance still passing.

The geometry-repair training run is `HLX-CLASSIFICATION-V2-GEOMETRY-REPAIR-20260930`. Restored checkpoint is epoch 9 of 12, primary weights `449bf3b303c95bc5d6b7d87173d50315616556c1379057414b970f3e5f0b18cf`. Selection score is 0.35176303097380063. Canonical logits stayed on the learned residual head.

Active-family macro-F1 is 0.1750422041280767. Non-exact-copy family macro-F1 is 0.03732057416267942. Three non-exact-copy families have F1 above 0: fashion-aesthetic, spiritual-mystic, and sports-competition. Those family-discrimination gates do not open.

Geometry on the same 296 validation family rows did improve. Pre-training median gold-versus-nearest-negative margin is -0.0238511860370636 with 172 high-collision rows. Post-training median margin is 0.09594389796257019 with 5 high-collision rows. Mean margin moves from -0.023349027127354732 to 0.09320517261575505.

Applicability invariance still passes. `none_surface_gap` is -0.023081016877715937. Residualized length correlation is 0.08844123652989021. Surface-cell F1 values remain at or above 0.80. Architecture validation is `INTERNAL_SHORT`. The reserve was not scored. BEST remains `9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6`.

The representation is more separable, but the residual head alone did not convert that into family F1. The next authorized step is a max-anchor family scorer on this repaired geometry, not another residual-only CE run and not reserve scoring.

### Max-anchor family scorer

`MAX_ANCHOR_FAMILY_SCORER_V1` is a validation-only scorer comparison on the repaired encoder. It does not train, does not score the reserve, and does not move BEST. Pinned inputs: geometry-repair primary `449bf3b303c95bc5d6b7d87173d50315616556c1379057414b970f3e5f0b18cf`, boundary `0ca6f34ce1abf68388e443371672ca36e16028079a175b6775e1968900e1c52f`, separation `ab698d342d2d276f81d4baf3fed609bb6f8bf88cd6810bb1d1998c5e409f63c3`. Canonical max-anchor score is `max cosine` to that family's sealed anchors. Family prediction is `argmax` over the 19 active families with vocabulary-order ties. NONE, ABSTAIN, and AMBIGUOUS are not family rows.

On 296 validation family-positive rows, residual macro-F1 is 0.1750422041280767, max-anchor macro-F1 is 0.1664857822906154, and diagnostic 1:1 z-score fusion macro-F1 is 0.20206957575241874. Max-anchor ATOM/PROSE family macros are 0.19337540305282241 and 0.2177426324431769. Max-anchor breadth is 7 families with F1 above 0, 6 at or above 0.20, 4 at or above 0.50, and 3 non-exact-copy families with F1 above 0. Decision is `MAX_ANCHOR_SCORER_REJECTED`. Canonical integration is not justified. Artifact sha256 `7475d6d9a5c7ccb20a554a56b1de5ceee1d85e2a90b5976035f920bab7f53d07`.

The diagnostic fusion cleared 0.1961 and raised new-family nonzero count to 4, but fusion remains diagnostic only under this pass. Scorer mechanics are exhausted for rescuing the 19-way head. The next substantive question is ontology and training-definition separation, not another residual or max-anchor classifier patch.

### Active-family separability audit

`HYPERLEX_ACTIVE_FAMILY_SEPARABILITY_AUDIT_V1` is a read-only ontology/data audit on training-side definition prose. It does not train, does not score the evaluation reserve, and does not move BEST. Jev stays off. Encoder weights stay frozen on the geometry-repair overlay (`449bf3b303c95bc5d6b7d87173d50315616556c1379057414b970f3e5f0b18cf`) for representation metrics only. Pairwise linear probes fit on train definitions and evaluate on val definitions; they do not update the encoder.

OBSERVED and INFERRED supports are preserved separately. Reserve, spent, held-out, measurement, settlement, and Jev rows are excluded. Pairwise embedding metrics cover within/cross similarity, nearest-neighbor confusion, centroid distance, and sealed-anchor collision rate. Lexical metrics use deterministic Dirichlet-prior log-odds over definition tokens.

Sealed artifact sha256 `2cb2fe2459a86323dfa8aa50136bb8e6822598ffd8895a1988af459949853d5f`. Pairwise embedding matrix sha256 `3957e4cefabf37a7d8993f0574c7a76c93096c0cd991b8a7134207e07ade7bda`. Lexical matrix sha256 `1579d47aabbb4429b352ad7c251b79b4f5722506d80d0cc25afd7a8d251ce3a5`.

Family status: `UNDER_SUPPORTED` for `betting-sharp`, `internet-slang`, and `memetic`; `OVERLAPPING` for ten families including the bulk of the 15-family collapse cluster plus `ai-native`; `NOISY` for `music-entertainment`, `regional-cultural`, `relationship-dating`, and `workplace-career`; `UNRESOLVED` for `gaming-meta` and `crypto-degen`. No family sealed as `SEPARABLE`.

Pair flags across 171 unordered pairs: `DATA_TOO_SPARSE` 51, `REPRESENTATION_COLLAPSE` 99, `ONTOLOGY_OVERLAP` 71, `LABEL_NOISE` 112, `SEPARABLE` 4. Pairwise probes are computable for 136 pairs; median probe F1 is 0.3333 with only 6 pairs at or above 0.80. Lexical log-odds often find enriched tokens, so `DEFINITION_TOO_GENERIC` does not dominate the flag table, but representation collapse and failed probes show the training definitions still do not carve mutually exclusive family geometry.

Sparse-family treatment refuses ontology failure from support alone. Additional data is judged plausible for `betting-sharp`, `internet-slang` (58 val definitions available), and `memetic`. Suspected label-noise rows are flagged without automatic relabeling.

Overall decision: `MIXED_REMEDIATION_REQUIRED`. The current 19-family ontology cannot be learned from the current training evidence. Next engineering action is mixed remediation: expand direct positive definition support for sparse families, clean the flagged noisy rows, and refine or refactor mutually non-exclusive collapse-cluster boundaries before any further scorer or encoder training.

### Active-family mixed remediation

`HYPERLEX_ACTIVE_FAMILY_MIXED_REMEDIATION_V1` turns the sealed separability audit (`2cb2fe2459a86323dfa8aa50136bb8e6822598ffd8895a1988af459949853d5f`, decision `MIXED_REMEDIATION_REQUIRED`) into an ordered non-mutating plan. It does not train, does not score the reserve, does not move BEST, and does not change the active ontology.

Phases: `PHASE_A_DATA_AND_NOISE` (expand sparse-family train definitions to >=12 and human-review suspected label-noise rows), `PHASE_B_BOUNDARY_REFINEMENT` (record positive/exclusion cues for overlapping/noisy families without mutating the sealed boundary artifact yet), `PHASE_C_ONTOLOGY_REFACTOR_REVIEW` (operator KEEP/MERGE/SPLIT review of the 13-family collapse overlap component), then `PHASE_D_REAUDIT_BEFORE_TRAINING`.

Training gate remains closed for encoder training, family-scorer training, reserve scoring, and BEST moves until phases A–C complete and a fresh separability audit no longer requires mixed/ontology remediation without waiver.

Artifact sha256 `d1292e106ae674d16967d85486133c912390de8afeb2ae5fcf977dd69cac1e00`. Next engineering action: execute PHASE_A for `betting-sharp`, `internet-slang`, and `memetic`, and review the 7 suspected label-noise rows.

### Active-family phase execution

`HYPERLEX_ACTIVE_FAMILY_PHASE_EXECUTION_V1` executes the sealed mixed-remediation plan. It does not train, does not score the reserve, does not move BEST, and does not mutate the active ontology.

PHASE_A acquired prose train definitions for sparse families to >=12 each (`betting-sharp` 14, `internet-slang` 13, `memetic` 13) with MediaWiki provenance and sealed 7 label-noise decisions (3 KEEP, 1 RELABEL, 3 DROP). Acquire export sha256 `2bfe35bbf39ee13dab3ffcb889961132e8529b1d1f6d47dd52633ff9d5ab610f`.

PHASE_B recorded positive/exclusion cue packs for overlapping/noisy/unresolved families for a future boundary re-seal without mutating `FAMILY_SEMANTIC_BOUNDARIES_V1`.

PHASE_C operator review kept the active vocabulary. The 13-family collapse component is `KEEP_WITH_BOUNDARY_REDEFINITION`; first-review pairs are SPLIT_CANDIDATE (approval-disapproval/social-status, approval-disapproval/relationship-dating, relationship-dating/social-status). No automatic merge.

PHASE_D re-ran the separability audit on remediation overlay `civilian.v0.4.phase.jsonl` (sha256 `8a934806885fb939f8b4ca26f10ab5bc6600c495d3be77d5a2366dc6c62146e0`). Decision remains `MIXED_REMEDIATION_REQUIRED` (artifact sha256 `d56d03420e7f7072b1798a55e7ecd8877263b1dfd4ad938d36115cba18a21d0a`): sparse under-support is largely cleared, but ontology overlap and representation collapse persist. Training gate stays closed.

Phase-execution artifact sha256 `6d11eab035d64a5ef8d1008ade9b565064920e6de2cc86673202cbc60753be3b`. `phases_complete=true`.

