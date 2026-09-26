# Evaluation reserve (GEN-0)

Text identity is `hyperlexical.holdout_guard.normalized_text_sha256`.
That is SHA-256 of `heldout_census.normalize_group_text`: NFKC, casefold, URL strip, non-alphanumeric to space, whitespace collapse. Empty normalized text still hashes. No second normalizer is an identity. `soft_ceiling.clean_surface` remains the unbind-clean slice predicate only.

Row ids are historical labels. One text identity may carry many row ids. Contamination, spending, abandonment, and reserve membership attach to the text hash.

## Exhaustion

On 2026-09-26 the live store (`01c1b38fd6e926962e47a520228e884ae7d99ea0ad6bbe188dc9980064254ac2`, 5005 rows) had **zero** rows eligible for a fresh holdout after split=test, the pinned morph78 export (`64b7d3dede25047cb6dd2e5b663f7fa72946ec82ac1a8816ae34622d1aaac430`, 9150 rows), spent v2, rc1 unbind rows, and the abandoned SELECT-001 / SELECT-002 holdouts. The 440 `split=test` rows are also training-consumed under the canonical hash, so dropping the split gate does not open a fresh classify set. Classify OBSERVED and classify non-none in that eligible universe are 0.

SELECT-001 is `CLOSED_AT_LAUNCH_GATE`. SELECT-002 is `EXECUTION_INVALID` (0 epochs, 0 gradient steps). Both holdouts are `UNSCORED_ABANDONED`: never scored, not reusable, not `SCORED_SPENT`. Manifest bytes stay as sealed. Do not reopen either experiment.

## Lifecycle

New text is routed **before** training exposure. Records are append-only. Flags that mean consumed, spent, or abandoned only turn on.

```text
NEW
 |
 +--> TRAIN_CANDIDATE
 |       |
 |       +--> TRAIN_CONSUMED
 |
 +--> EVAL_RESERVE
         |
         +--> EVAL_BOUND
                 |
                 +--> EVAL_SPENT
                 |
                 +--> EVAL_ABANDONED
```

`AVAILABLE` is catalogued text with none of those flags. It may still be routed to `TRAIN_CANDIDATE` or `EVAL_RESERVE`.

Forbidden without a governed generation reset:

- `EVAL_RESERVE` or `EVAL_BOUND` later entering training
- training-consumed text later used as unseen evaluation
- spent or abandoned text returning to the fresh reserve

A generation-reset **request** can be recorded. It does not clear flags and it does not create a new baseline. GEN-1 is not opened by this policy.

## Assignment

Policy id: `hyperlex.eval_reserve.v1`. Fixed before any candidate output is observed. Model scores, errors, and predictions are refused as admission inputs.

Within a batch, identities are ordered by `sha256(GEN-0 | batch_id | normalized_text_sha256)`. A new identity is `EVAL_RESERVE` when it still fills at least one open required slice. Otherwise it is `TRAIN_CANDIDATE`. Quotas are unique text identities, not raw rows. A second row id on an existing hash does not increase the evaluation sample size. A new hash that reuses an old row id stays a different identity and is reported as a collision.

Required slices, because checkpoint selection needs each of them:

- `classify` (classification accuracy)
- `classify_observed` (OBSERVED-label accuracy)
- `classify_non_none` (`classify_macro_f1_nonnone`)
- `unbind_clean` (unbind clean exact)

## Coverage classes

| Claim | Class |
| --- | --- |
| Canonical text hash is the contamination identity | CANONICAL_REQUIREMENT |
| Fresh evaluation text is disjoint from training, spent, and abandoned text | CANONICAL_REQUIREMENT |
| Each required slice is represented before SELECT-003 can be drafted | CANONICAL_REQUIREMENT |
| Statistical minimum n for those metrics | NOT_COMPUTABLE |
| v2 `DRAW_READY_MIN` 470 | HISTORICAL_PRECEDENT (unbind census target; PR #113 sets no v2 size) |
| Name-gate 2500 | CANONICAL_REQUIREMENT for the name gate, not for this holdout |
| rc1 classify_clean 444 / OBSERVED 72 / unbind_clean 306 | HISTORICAL_PRECEDENT (spent test) |
| SELECT-002 eligibility 606 classify / 287 OBSERVED / 604 non-none / 250 clean unbind | HISTORICAL_PRECEDENT and the PLANNING_TARGET |

The planning target restores that SELECT-002 shape. It is not a validity theorem. Gap versus a statistical minimum is `NOT_COMPUTABLE`.

## Admission

```sh
PYTHONPATH=scripts/shadow python -m hyperlexical.identity_ledger admit \
  --ledger /path/to/ledger --rows new.jsonl --batch-id BATCH --source acquire
```

A row is accepted only when its canonical hash is absent from `TRAIN_CONSUMED`, `EVAL_SPENT`, `EVAL_ABANDONED`, and the existing reserve. The command reports raw rows and unique canonical text identities. Reserve rows must not be used for training, checkpoint selection, hyperparameter tuning, candidate-specific error review, or repeated scoring. Aggregate census counts are allowed. When `HLX_EVAL_RESERVE_LEDGER` is set, the trainer refuses if a loaded training row is still `EVAL_RESERVE` or `EVAL_BOUND`.

## SELECT-003

Do not draft SELECT-003 until a new reserve exists, the four slices are represented, the reserve is text-disjoint from the pinned training export, the reserve is not spent or abandoned, and this policy stays sealed. The unresolved hypothesis, if a later authorization allows it, is still `HLX_SELECT_METRIC`: `unbind_exact` versus `classify_macro_f1_nonnone`. Authorization is a separate act. Meeting a planning target does not grant it.

## GEN-0 and GEN-1

GEN-0 keeps `seed-morph78` and the pinned 9150-row export as the training baseline. New material is evaluation-only until the reserve slices are filled. Overflow may become `TRAIN_CANDIDATE` and must not be pulled back into the reserve.

GEN-0 becomes impractical only if, after a real acquisition attempt:

- new classify evidence cannot represent OBSERVED and non-none together
- new text keeps colliding with the pinned export or with spent/abandoned hashes
- accepted training candidates grow while the reserve slices stay empty
- the reserve cannot hold the four slices at once
- the historical baseline is no longer the system under test

Convenience is not one of those conditions. This document does not create GEN-1.

## Ledger

`scripts/shadow/hyperlexical/build_identity_ledger.py` catalogues receipt-backed artifacts. It does not infer lifecycle from filenames. The populated ledger stays on the host store, not in git, and does not contain raw text.

## Acquisition batch HLX-EVAL-ACQ-2026-09-26-001

Screened local rights-cleared and operator-labeled corpora. The ledger was not mutated. Decision `REJECT_BATCH`. The reserve stays empty.

- 2026 backfill atoms: 67/67 unique hashes already `TRAIN_CONSUMED`.
- Harvest multiword file: 890/890 unique hashes already `TRAIN_CONSUMED`.
- Civilian seed: 17 novel identities, all lineage `ai-native`. A registry export marked `OBSERVED` is not an operator settlement, so those rows were held. Class imbalance is severe. No balance threshold is declared.
- 2026-09-16 structure gold: the authorized train rows are already consumed. Four novel leftovers carry model predictions and were excluded.
- Agent-memetics seeds: rights are unresolved and task labels are absent.

New `OBSERVED` coverage is `NOT_COMPUTABLE` until an operator harvest settlement exists. This record does not settle phrases. SELECT-003 stays undrafted. GEN-1 was not created. In-repo settled gold is exhausted. That alone does not reset GEN-0.

## Acquisition batch HLX-EVAL-ACQ-2026-09-26-002

The held-out stream (`hs-20260925T211358Z`, 339 rows) is the shelf that sits beside the Jev lane. Every canonical text hash is absent from the identity ledger. Overlap with the box Jev exposure list is 0. The ledger was not mutated. Decision: not admitted. The reserve stays empty.

Jev in this batch is the exposure fence. `hs_run.py` and each row policy forbid evaluating Jev, the lineage rule, or any other model on these rows. `JEV_API_KEY` is unset on this host. No vendor call was made. A Jev family call is not an operator settlement.

- Rights-cleared INFERRED labels: gaming-meta 99, betting-sharp 61, crypto-degen 5, plus 40 encyclopedic `none`. Five families have no independent label.
- 134 rows are `UNLABELLED`. The attest column is empty on all 339 rows, so new `OBSERVED` coverage is `NOT_COMPUTABLE`.
- 16 Reddit and Know Your Meme rows have unresolved rights.
- Class imbalance on the rights-cleared non-none subset is severe. No balance threshold is declared. Admitting it would open `classify_macro_f1_nonnone` on three families.

SELECT-003 stays undrafted. GEN-1 was not created. Novel yield against `TRAIN_CONSUMED` is 339/339, so GEN-0 is not collision-blocked. The next label step is operator `attest-apply` on the queued sheet.

## Taxonomy proposal HLX-EVAL-TAXON-2026-09-26-001

The next label step is no longer `attest-apply`. The operator directed a taxonomy expansion first. Draft: `label-taxonomy-proposal.md`. Private remap receipt has no row text. The ledger was not mutated. Nothing was admitted. Jev was not called. `attest-apply` was not run.

The production head stays the nine-way `layout.FAMILIES` list. The proposal adds sixteen non-none names as a draft active set, with `attest`, `register`, and `function` as separate surfaces. `evaluation.enabled` is false on every name. Support minimum is `NOT_COMPUTABLE`.

Of the 339 stream rows, 204 keep the same family as a `PROPOSED_REMAP` (gaming-meta 98, betting-sharp 61, crypto-degen 5, none 40). 135 are `LABEL_UNRESOLVED`. `brainrot-aura` is not split. Kinship hints are not mapped to `relationship-dating`. Eleven of the sixteen names have no row on this shelf. Row settlement is not ready. SELECT-003 stays undrafted.

## Taxonomy acceptance HLX-EVAL-TAXON-2026-09-26-002

The operator accepted the ontology structure and amended it. Active non-none families are eighteen, including `identity-affiliation` and `politics-civic`. `work-hustle` is renamed `workplace-career`. `brainrot-aura` is not a family. Six names stay candidates. `taxonomy.active` is true and `evaluation.enabled` is false on all eighteen. `none` stays abstain. `source_hint` is evidence, not `semantic_family`.

Lanes are prepared and unsettled: A 204, B 65, C 21, D 16. Thirty-three Wiktionary hint-only rows sit outside those lanes and stay `LABEL_UNRESOLVED`. Decision cells are empty. `attest-apply` was not run. The current command would force `OBSERVED` and would reject the new names, so it must not be used on these sheets. Vendor calls: 0. Reserve stays 0. SELECT-003 stays undrafted.


## Settlement tool HLX-EVAL-SETTLE-2026-09-26-001

Evaluation settlement is a separate command, `python -m hyperlexical.identity_ledger settlement-apply`. Production `attest-apply` was not modified and was not run. That command still accepts only the production families plus `none` or `reject`, and it still writes `label_source=OBSERVED` for an accepted value.

`settlement-apply` reads completed operator cells. It does not fill them. `source_hint`, `semantic_family`, and `attest` are separate fields. `ACCEPT` stores the attest the operator entered and does not promote existing evidence to `OBSERVED`. `RECLASSIFY` requires an explicit family that differs from the proposed evidence. `NONE` stores `semantic_family=none` and is not `reject`. `UNRESOLVED` stores null family and null attest. A second decision for the same row is refused. The log and the receipt are append-only and contain no row text.

`taxonomy.active`, `evaluation.enabled`, and `production.enabled` are three flags. The eighteen families stay taxonomy-active only. Both enable flags stay false. `layout.FAMILIES` is unchanged. Lanes A–D and the hint-only holding sheet were validated with every decision cell empty (204 / 65 / 21 / 16 / 33). Rows settled: 0. Unresolved decisions: 0. Reserve added: 0. Vendor calls: 0. The identity ledger was not mutated. SELECT-003 stays undrafted.


## Operator settlement HLX-EVAL-SETTLE-2026-09-26-002

The five private sheets for stream `hs-20260925T211358Z` were filled with an explicit decision on every row, then applied with `python -m hyperlexical.identity_ledger settlement-apply`. Production `attest-apply` was not run. `layout.FAMILIES` was not edited. No row text is in this file.

Blank and `UNRESOLVED` stay distinct. Blank means the operator has not reviewed the row. `UNRESOLVED` means the operator reviewed the row and declined to settle it. This pass left blank at 0 and `UNRESOLVED` at 84.

Counts: settled 255 (`ACCEPT` 204, `RECLASSIFY` 32, `NONE` 19), `UNRESOLVED` 84, blank 0. `OBSERVED` 128. `INFERRED` 127. Rights-blocked settled 14. Those 14 stay out of `EVAL_RESERVE`. Rights status was not changed by the semantic decision.

`OBSERVED` was used only when a stored gloss or the row text directly states the settled family, the atom is slangish or multiword jargon, and the primary stored sense is that family. A category, a topic, or `source_hint` did not set family or attest. Accepting a family did not promote an existing `INFERRED` label. Encyclopedic `none` rows stayed `INFERRED`.

Settled support by unique canonical text, including zeros: gaming-meta 60 (OBSERVED 38, INFERRED 22, cleared 60, blocked 0); betting-sharp 58 (41, 17, 53, 5); crypto-degen 4 (3, 1, 3, 1); internet-slang 19 (10, 9, 19, 0); memetic 3 (0, 3, 2, 1); social-status 6 (3, 3, 6, 0); relationship-dating 0; approval-disapproval 1 (0, 1, 1, 0); conflict-aggression 0; technology-ai 4 (1, 3, 4, 0); workplace-career 10 (9, 1, 10, 0); sports-competition 1 (0, 1, 0, 1); music-entertainment 1 (0, 1, 1, 0); fashion-aesthetic 0; regional-cultural 0; spiritual-mystic 0; identity-affiliation 16 (13, 3, 16, 0); politics-civic 13 (10, 3, 13, 0); none 59 (0, 59, 53, 6).

Rights-cleared settled non-none identities: 188. Quantitative support thresholds are `NOT_COMPUTABLE`, so no `UNREPRESENTED` / `LOW_SUPPORT` / `REPRESENTED` flag is assigned. `OBSERVED` total 128, all non-none; `OBSERVED` none is 0.

One workplace-lane row describes retail product reformulation and price-tier inflation. `finance-retail` remains a candidate and was not activated. That row is `UNRESOLVED`.

Admission used `identity_ledger admit` under `hyperlex.eval_reserve.v1`, batch `HLX-EVAL-ADMIT-2026-09-26-002`. Admitted to `EVAL_RESERVE`: 241. Rejected existing identities: 0. Slice counts after admission: classify 241, classify_observed 123, classify_non_none 188, unbind_clean 0. `clean_unbind_support` is 0. This stream has no unbind target and none was fabricated. SELECT-003 was not drafted. The gate reports `eligible: false` because `unbind_clean` is unrepresented. Reserve identities are text-disjoint from the pinned train export.

Receipt `HLX-EVAL-SETTLE-2026-09-26-002` sha256 `1b0fb54a5de0fb708f74ad278037458c15e0abea5a7eb6b4b151b7e7fb34567e`. `settlement-apply` still records `reserve_added: 0`; admission is the separate ledger command. Vendor calls: 0. BEST was not moved. Do not train.


## Clean-unbind contract — 2026-09-26

Phase: clean-unbind capacity recovery. The 241 classify reserve identities stay protected. This section does not retune `semantic_family`, `attest`, or `evaluation.enabled`.

Executed shape: `hyperlexical.export._unbind_dual_scheme_rows`. Fillers are the source atom's own tokens. Positional text is those tokens joined by spaces, with roles `pos_0..pos_n-1`. Type-slot text is `TOKEN:` / `SLOT:` / `MARKER:` prefixed by index, and the fillers stay the same tokens. Role schemes are only `positional` and `type_slot`. Token count is 2 through `LIVE_UNBIND_MAX_TOKENS` (6). Atom length is at most `LIVE_UNBIND_MAX_LEN` (80). A gloss is not unbind gold. `class` is copied, not invented; this acquisition uses `INFERRED` and `lineage=none`.

Contamination identity: `hyperlexical.holdout_guard.normalized_text_sha256` (NFKC, casefold, URL and punctuation stripped, SHA-256).

Clean predicate: `soft_ceiling.clean_surface` on rows whose `split` is `train`, which is the call in `holdout_eligibility.census`. Definition string: `unbind_clean_definition = soft_ceiling.clean_surface`. The clean predicate is whitespace-collapsed lowercase equality of the row text against train text. It is not the contamination hash. `oov_filler_surface` is a different surface and is not this predicate.

Scorer, not run in this phase: `hyperlexical.eval_forward.score_unbind_exact`. Gold is the filler list. Empty filler lists are skipped. Metrics are `unbind_exact`, `unbind_token_f1`, `unbind_slot_f1`, and the strict variants, including `by_role_scheme`. Baseline name: `unbind_copy_token`.

Synthetic row, placeholders only:

```json
{
  "text": "EXAMPLE_TOKEN_A EXAMPLE_TOKEN_B",
  "split": "eval",
  "lineage": "none",
  "typology": [],
  "stage": "noise",
  "roles": ["pos_0", "pos_1"],
  "fillers": ["EXAMPLE_TOKEN_A", "EXAMPLE_TOKEN_B"],
  "role_scheme": "positional",
  "task": "unbind",
  "provenance": "source:EXAMPLE_LOCATOR",
  "class": "INFERRED",
  "license": "EXAMPLE_RIGHTS_GRANT",
  "target_origin": "source_lemma_tokens"
}
```

The type-slot twin uses text `TOKEN:EXAMPLE_TOKEN_A SLOT:EXAMPLE_TOKEN_B`, roles `TOKEN` and `SLOT`, and the same fillers. Unbind settlement decisions are `ACCEPT`, `CORRECT_TARGET`, `REJECT`, and `UNRESOLVED` in `hyperlex.eval_unbind_settlement.v1`. That log is not the classify settlement schema. Admission still goes through `IdentityLedger.admit`. `unbind_clean` is set only for hashes kept by `clean_surface`.



## Clean-unbind admission HLX-EVAL-ADMIT-2026-09-26-003

Source: Princeton WordNet 3.0 index lemmas (`index.noun`, `index.verb`, `index.adj`, `index.adv`). Glosses in `data.*` were not read and were not used as targets. Raw artifact sha256 `cbda5ea6eef7f36a97a43d4a75f85e07fccbb4f23657d27b4ccbc93e2646ab59`. License file sha256 `7731175a77952e259390b496fab905e57118b8d19ad3a8383c67eee724ff443f`. Rights: WordNet 3.0 Copyright 2006 by Princeton University, with permission to use, copy, modify, and distribute for any purpose without fee or royalty when the notice is preserved. Unresolved-rights rows were not in this source.

Fillers are the source lemma tokens (`target_origin=source_lemma_tokens`). Operator settlement `HLX-EVAL-UNBIND-SETTLE-2026-09-26-001` appended 250 `ACCEPT` events on that basis. `CORRECT_TARGET` 0. `REJECT` 0. `UNRESOLVED` 0. Settlement receipt sha256 `3ada2dae58bde22ef1ed1ac5a4004be75d7bf3f52cac590f24900de71015194b`. The classify settlement log was not rewritten.

Screen of shaped dual-scheme rows: 128233 unique texts. Novel and clean: 128044. Rejected `TRAIN_CONSUMED` 184. Rejected existing `EVAL_RESERVE` 5. Those 5 were not reused. Novelty rate among shaped rows: 0.9985. Planning cap admitted 250 of the admissible set. `IdentityLedger.admit` appended 500 events. Events sha256 before `f5e0008f27a80b11bc7e5b98e48e9e99cada04ee8f9455ed5ece6f99c1de3266`, after `8223ae11bb42bd1a98ebcd739d1cfbc470085e241826b662703faefdfe752da6`. Routed to `TRAIN_CANDIDATE`: 0. Acquisition receipt sha256 `be5671d4cf586b7a9ce3f45b4f5b8b5d0574edd4d1eaeef0c9644ca8ad2678a8`. Admission receipt sha256 `53df5397a13974e03bd60310fca2c29589e7a0fa6236dd576cf4ddf43a75bf15`. Census receipt sha256 `a5e9ae8ef6b65b5c187633e09b8700a5ef800eb1d97bd7a78aa2a9db26cf0a16`.

Reserve after admission: classify 241, classify_observed 123, classify_non_none 188, unbind_clean 250. The first three did not decrease. Admitted rows are `class=INFERRED`, `lineage=none`. Role schemes: positional 125, type_slot 125. Filler counts: 2 tokens 64, 3 tokens 56, 4 tokens 56, 5 tokens 46, 6 tokens 28. Source-index metadata, not a Hyperlex family: noun 72, verb 68, adv 62, adj 48. Unique filler targets: 125. Each target has 2 surfaces (the two role schemes). Maximum surfaces per target: 2.

Planning progress, not a validity threshold: classify 241/606, OBSERVED 123/287, non-none 188/604, clean unbind 250/250. Statistical minimum remains `NOT_COMPUTABLE`.

`select_003_gate.eligible` is true. `training_overlap_identities` is 0. `spent_or_abandoned_in_reserve` is 0. Reserve identities 491. SELECT-003 was not drafted. This is representation completeness, not training readiness. Evaluation quality is still one lexicon, `INFERRED`, `lineage=none`. These rights-cleared active families still have zero settled classify support and were not collected here: relationship-dating, conflict-aggression, sports-competition, fashion-aesthetic, regional-cultural, spiritual-mystic.

Vendor calls: 0. BEST was not moved. Do not train.


## SELECT-003 preregistration HLX-EXP-2026-09-26-SELECT-003

Phase: preregistration only. Experiment id `HLX-EXP-2026-09-26-SELECT-003`. Training is not authorized. BEST is not moved. No holdout is scored. Vendor calls: 0.

Predecessors are not evidence for or against the hypothesis. SELECT-001 closed at the launch gate with the hypothesis `UNTESTED`. SELECT-002 is `EXECUTION_INVALID` with epochs 0 and gradient steps 0, hypothesis `UNTESTED`.

Hypothesis: with training otherwise equivalent to the reconstructed `seed-morph78` baseline, does selecting checkpoints by `classify_macro_f1_nonnone` improve non-none classification macro-F1 while preserving the established unbind and classification safeguards?

The single scientific variable is `HLX_SELECT_METRIC`. Baseline: unset, which resolves to `unbind_exact`, with `HYPERLEX_SAVE_BEST_UNBIND=1`. Candidate: `classify_macro_f1_nonnone`. Frozen with the reconstructed recipe: `HYPERLEX_FILLER_FILTER=off`, `HYPERLEX_TASK_ROUTING=legacy_split`, `HYPERLEX_UNBIND_LOSS_WEIGHT=1.0`, init `seed-morph65`, `HLX_SEED` unset, `HLX_E2_DISJOINT` absent, `HLX_VOCAB_TRAIN_ONLY` absent, `HLX_ALLOW_NO_HOLDOUT` unset, `HYPERLEX_RELEASE_SET` absent. Pinned-export execution is infrastructure, not a scientific variable. Checkpoint selection inside the trainer still uses the pinned export's val split. The reserve is the comparison surface for the decision rule. Substituting the reserve for that val split is a second variable and is not part of this experiment.

Training input: pinned export, 9150 rows, sha256 `64b7d3dede25047cb6dd2e5b663f7fa72946ec82ac1a8816ae34622d1aaac430`. Rows before the reserve filter 9150, after 9150. Reserve/training row-id overlap 0. Reserve/training text-hash overlap 0. Any difference is an admission failure.

BEST remains `hyperlex-encoder-modernbert-base-seed-morph78`, weights sha256 `fc53676bd347cccd4d0ac9a429f3469c36436f8eb0e09954e0c347c7b133a4a1`. Trunk weights sha256 `340ac08b74eef0d7bdec2d7981a6a3d4249bf0e6aab60634b72ad02c2b8023a9`. `layout.FAMILIES` was not edited.

The bound GEN-0 reserve is unchanged: classify 241, classify_observed 123, classify_non_none 188, unbind_clean 250, identities 491. Events sha256 `8223ae11bb42bd1a98ebcd739d1cfbc470085e241826b662703faefdfe752da6`. Ledger projection sha256 `d071b7aec8154203ce7f9ae9531639b8d638f86c2ac0c3af38bead9b3c4a48f9`. Spent 0. Abandoned 0. Text-disjoint from training. Rights-cleared. No identities are added or removed under this experiment id.

Receipts bound with the reserve: classification settlement `HLX-EVAL-SETTLE-2026-09-26-002` canonical sha256 `1b0fb54a5de0fb708f74ad278037458c15e0abea5a7eb6b4b151b7e7fb34567e`; classification admission `HLX-EVAL-ADMIT-2026-09-26-002` sha256 `9898d13140b1adf9e496ce4a7e71f9573d3a0f87e97355ea01de3ecafb66e836`; clean-unbind acquisition `be5671d4cf586b7a9ce3f45b4f5b8b5d0574edd4d1eaeef0c9644ca8ad2678a8`; clean-unbind settlement `3ada2dae58bde22ef1ed1ac5a4004be75d7bf3f52cac590f24900de71015194b`; clean-unbind admission `53df5397a13974e03bd60310fca2c29589e7a0fa6236dd576cf4ddf43a75bf15`; census `a5e9ae8ef6b65b5c187633e09b8700a5ef800eb1d97bd7a78aa2a9db26cf0a16`.

Primary metric:

```text
name: classify_macro_f1_nonnone
label_universe_sha256: 227b782011aad7e693fde253e103a24b3ca0bd6b04e090d446656fa943bf0175
absent_class_policy: omit_when_gold_support_is_zero
scorer: hyperlexical.classify_metrics.macro_f1_nonnone
```

The sealed class set is the non-none lineages present on the bound reserve, with identity support: approval-disapproval 1, betting-sharp 53, crypto-degen 3, gaming-meta 60, identity-affiliation 16, internet-slang 19, memetic 2, music-entertainment 1, politics-civic 13, social-status 6, technology-ai 4, workplace-career 10. Sum 188. The scorer's macro is the unweighted mean of per-class F1 over gold labels other than `none` that have support n>0. Classes with gold support 0 are omitted. They are not entered as F1=0. A later taxonomy expansion does not enter this experiment's metric. The six families with zero rights-cleared settled support stay outside the universe: relationship-dating, conflict-aggression, sports-competition, fashion-aesthetic, regional-cultural, spiritual-mystic.

Slice mapping, one contamination function for every slice (`normalized_text_sha256`):

- `classify_macro_f1_nonnone` uses the 188 `classify_non_none` identities. Gold is `lineage`. The 53 `none` identities are not in this row set.
- Classification accuracy uses the 241 `classify` identities. Gold is `lineage`, including `none`. Scorer: `accuracy`.
- OBSERVED-label accuracy uses the 123 `classify_observed` identities. Gold is `lineage`. Scorer: `accuracy`. These three slices share classification settlement `HLX-EVAL-SETTLE-2026-09-26-002` and admission `HLX-EVAL-ADMIT-2026-09-26-002`.
- Unbind clean exact uses the 250 `unbind_clean` identities. Gold is the filler list. Scorer: `score_unbind_exact` (`unbind_exact`). Settlement is `HLX-EVAL-UNBIND-SETTLE-2026-09-26-001`, not the classify log. Clean predicate remains `soft_ceiling.clean_surface`.

Decision thresholds are `BLOCKED_PENDING_OPERATOR_AUTHORIZATION`. Inherited authorization from SELECT-002 is `NOT_COMPUTABLE`. No canonical rule carries numeric margins across an execution-invalid predecessor, and SELECT-002 sealed its margins for that experiment id only. Preservation names are prepared and inactive: unbind clean exact, classification accuracy, OBSERVED-label accuracy. Promote and reject thresholds are not set.

Representation completeness passes. Training provenance passes. Holdout disjointness passes. Rights and provenance pass. Clean-unbind capacity passes. Evaluation quality is limited and disclosed: non-none support is 188 and imbalanced, and the 250 clean-unbind rows are Princeton WordNet 3.0 only, all `INFERRED`, `lineage=none`, 125 filler targets, 2 surfaces per target. The experiment is not authorized to run.

## SELECT-003 threshold authorization — 2026-09-26

Operator decision for `HLX-EXP-2026-09-26-SELECT-003` only. This is a new authorization. It does not transfer SELECT-001 or SELECT-002 margins. The sealed preregistration file is not edited. Training is not authorized. BEST is not moved. The reserve is not scored.

Primary metric remains `classify_macro_f1_nonnone`. Label universe sha256 `227b782011aad7e693fde253e103a24b3ca0bd6b04e090d446656fa943bf0175`. Absent-class policy `omit_when_gold_support_is_zero`. The universe stays the twelve supported non-none classes on the sealed reserve.

Comparison baseline is `hyperlex-encoder-modernbert-base-seed-morph78`, weights sha256 `fc53676bd347cccd4d0ac9a429f3469c36436f8eb0e09954e0c347c7b133a4a1`, scored later on the same GEN-0 reserve: classify 241, classify_observed 123, classify_non_none 188, unbind_clean 250.

`PROMOTE` requires every condition. Primary: candidate `classify_macro_f1_nonnone` strictly greater than seed-morph78. Equality does not promote. Unbind clean exact on the 250 sealed identities stays within 0.01 below seed-morph78. Classification accuracy on the 241 sealed identities stays within 0.02. OBSERVED-label accuracy on the 123 sealed identities stays within 0.05. Integrity must also pass: one scientific variable, pinned export exact, 9150 rows before and after the reserve filter, row-id overlap 0, canonical text-hash overlap 0, no reserve identity spent or abandoned before scoring, sealed ledger unchanged, sealed class universe unchanged, checkpoint selection follows `HLX_SELECT_METRIC`, complete provenance, no contamination-guard failure, no schema or name-gate failure, and no `CHAR_WINS`.

`REJECT` if the candidate primary metric is lower, or the unbind delta is below -0.01, or classification accuracy delta is below -0.02, or OBSERVED-label accuracy delta is below -0.05, or any hard failure occurs: `CHAR_WINS`, more than one scientific variable, training input other than the sealed pin, effective training rows other than 9150, reserve binding change, class-universe change, unverifiable reserve or execution provenance, or a hard integrity or contamination guard failure.

`INCONCLUSIVE` if the primary metrics are equal and the preservation and integrity guards pass. Also `INCONCLUSIVE` when execution and scoring are valid but the sealed rule cannot be applied deterministically, and that reason is not itself a hard integrity failure. An inconclusive result is not resolved by changing thresholds.

These floors are new SELECT-003 rules. A later promote would mean checkpoint selection by non-none macro-F1 improved the sealed twelve supported families without exceeding the three allowed regressions. It would not mean improvement across the eighteen-family ontology. Families outside the gold universe remain relationship-dating, conflict-aggression, sports-competition, fashion-aesthetic, regional-cultural, and spiritual-mystic. Representation completeness passes. Evaluation quality stays limited. Vendor calls: 0. Do not train.


## SELECT-003 execution HLX-EXP-2026-09-26-SELECT-003

One launch was authorized from Spark commit `53f128a68a6603a98d9d5a3e56cc357f4a17aa0c` with a clean tree. The sealed preregistration, threshold authorization, candidate environment, and non-launching preflight were not edited. `HYPERLEX_ALLOW_TRAIN=1` was a process overlay only. `HLX_ALLOW_NO_HOLDOUT` stayed unset.

Container `hlx-train-select003-1790441469` on `lmsysorg/sglang:dev-qwen38-27b-dflash2` (`sha256:616a3e97f45191af975896cfa644279096cb31bd408a071c2e99ca7209c3cafe`) started 2026-09-26T16:51:09Z and exited 1 at 2026-09-26T16:51:12Z. The trainer refused before `load_training_bundle`: `HYPERLEX_ALLOW_TRAIN=1` with no holdout manifest. Epochs 0. Gradient steps 0. No candidate checkpoint. The pinned export was not consumed. The reserve was not scored and was not spent. Decision `EXECUTION_INVALID`. The hypothesis is `UNTESTED`. This is not `PROMOTE`, `REJECT`, or `INCONCLUSIVE`.

BEST remains `hyperlex-encoder-modernbert-base-seed-morph78`, sha256 `fc53676bd347cccd4d0ac9a429f3469c36436f8eb0e09954e0c347c7b133a4a1`. Vendor calls: 0. Do not retry this experiment id. Do not train.
## SELECT-003 closed — PREFLIGHT_LAUNCH_HOLDOUT_GATE_MISMATCH

`HLX-EXP-2026-09-26-SELECT-003` is permanently `EXECUTION_INVALID`. Cause: `PREFLIGHT_LAUNCH_HOLDOUT_GATE_MISMATCH`. The non-launching preflight reported `TRAINING_READY` without running `require_holdout_for_training` under `HYPERLEX_ALLOW_TRAIN=1`. The trainer then refused before `load_training_bundle` because the sealed candidate had no `HLX_HOLDOUT_MANIFESTS` and `HLX_ALLOW_NO_HOLDOUT` stayed unset. Epochs 0. Gradient steps 0. Candidate checkpoint: none. Reserve scored: false. `BEST_moved`: false. Hypothesis: `UNTESTED`. The sealed preregistration and threshold authorization are not rewritten. This id is not retried.

## Controlled-experiment admission — CONTROLLED_RESERVE

The canonical controlled-experiment holdout contract is `CONTROLLED_RESERVE`. A launch with `HLX_EXPERIMENT_ID` set is admitted by `admit_training_run`, which both preflight and `run_loop` call, in this order: experiment binding, launch gate, sealed reserve, pinned training input, train/reserve disjointness, single scientific variable, BEST and trunk digests, output directory, then ready.

A sealed reserve binding satisfies the holdout requirement when the ledger is `EVAL_RESERVE`, all four slices are present, the binding digest matches `events.jsonl`, and training overlap by row id and by normalized text hash is 0. Overlap rejects the run. It does not drop training rows. `HLX_HOLDOUT_MANIFESTS` is not a second requirement. `HLX_ALLOW_NO_HOLDOUT` does not admit a controlled experiment. Legacy launches that are not controlled experiments still use the manifest gate.

`HYPERLEX_ALLOW_TRAIN=1` is part of the effective environment hash. `HLX_ADMISSION_ONLY=1` is not. With that flag, `python -m hyperlexical.train --run` returns after admission and does not construct an optimizer, enter epoch 0, or take a gradient step. `TRAINING_READY` means that same admission returned `ADMISSION_PASS`.

```text
RUNE.PREFLIGHT_LAUNCH_PARITY(x) =
    effective_environment_hash(preflight) == effective_environment_hash(launch)
    AND admission_gate_sequence(preflight) == admission_gate_sequence(launch)
    AND admission_result(preflight) == admission_result(launch)
```

## SELECT-004 readiness

`HLX-EXP-2026-09-26-SELECT-004` is not preregistered and is not authorized to run. It may be drafted. SELECT-001, SELECT-002, and SELECT-003 produced no scientific evidence about `HLX_SELECT_METRIC`. A draft may test the same hypothesis: baseline unset, which resolves to `unbind_exact` with `HYPERLEX_SAVE_BEST_UNBIND=1`; candidate `classify_macro_f1_nonnone`.

No canonical rule carries numeric thresholds across experiments. SELECT-003's floors do not transfer. SELECT-004 decision thresholds are `BLOCKED_PENDING_OPERATOR_AUTHORIZATION` until a fresh authorization is sealed for that id.

The draft must keep the pinned export sha256 `64b7d3dede25047cb6dd2e5b663f7fa72946ec82ac1a8816ae34622d1aaac430`, 9150 rows, BEST sha256 `fc53676bd347cccd4d0ac9a429f3469c36436f8eb0e09954e0c347c7b133a4a1`, and trunk sha256 `340ac08b74eef0d7bdec2d7981a6a3d4249bf0e6aab60634b72ad02c2b8023a9`. The GEN-0 reserve stays classify 241, classify_observed 123, classify_non_none 188, unbind_clean 250, identities 491. It is not scored and its lifecycle is not changed. Admission uses that reserve. It does not draw another one and it does not attach a legacy manifest.

Vendor calls: 0. BEST was not moved. Do not train.
## SELECT-004 preregistered — HLX-EXP-2026-09-26-SELECT-004

`HLX-EXP-2026-09-26-SELECT-004` is `PREREGISTERED`. Preregistration sha256 `365f7ce7141e8ee899fc52d85584a32c21ecfcb596e316b1438463bd8db85c4a`. That seal records repository commit `493c75981bf443baf2899b71b504fe7c7a529cf9` and a clean tree. Later documentation does not edit the sealed file.

Predecessors are not evidence. SELECT-001 remains `CLOSED_AT_LAUNCH_GATE`. SELECT-002 remains `EXECUTION_INVALID` with epochs 0 and gradient steps 0. SELECT-003 remains `EXECUTION_INVALID`, cause `PREFLIGHT_LAUNCH_HOLDOUT_GATE_MISMATCH`, epochs 0, gradient steps 0, candidate checkpoint none, reserve not scored. The hypothesis is `UNTESTED`.

The single scientific variable is `HLX_SELECT_METRIC`. Baseline is unset, which resolves to `unbind_exact` with `HYPERLEX_SAVE_BEST_UNBIND=1`. Candidate is `classify_macro_f1_nonnone`. Experiment diff sha256 `aa6e42e50a9547908edfe4860371a2ec05f7ec20ea87dfa829555d9e7b05bc4c`. `experimental_variable_count` is 1. Metadata differences are the experiment id, the output directory, and the residual-dump path.

`CONTROLLED_RESERVE` binding sha256 `c16e69559dd6582f687532ce6e2a2e9b52a70db1aa066d11e7e68e723936b371`. Ledger events sha256 `8223ae11bb42bd1a98ebcd739d1cfbc470085e241826b662703faefdfe752da6`. Projection sha256 `d071b7aec8154203ce7f9ae9531639b8d638f86c2ac0c3af38bead9b3c4a48f9`. Counts remain classify 241, classify_observed 123, classify_non_none 188, unbind_clean 250, identities 491, lifecycle `EVAL_RESERVE`. Training row-id overlap is 0. Training canonical-text overlap is 0. The reserve was not scored, spent, abandoned, or relabeled. Historical spent and abandoned identities in the same ledger are not this reserve.

Training input is the pinned export sha256 `64b7d3dede25047cb6dd2e5b663f7fa72946ec82ac1a8816ae34622d1aaac430`, mode `PINNED_EXPORT`. Declared rows, consumed rows, and effective optimization rows are 9150. No runtime exclusion reduced the set. `HLX_ALLOW_NO_HOLDOUT` stayed unset. No legacy holdout manifest was attached.

BEST remains `hyperlex-encoder-modernbert-base-seed-morph78`, sha256 `fc53676bd347cccd4d0ac9a429f3469c36436f8eb0e09954e0c347c7b133a4a1`. Trunk sha256 `340ac08b74eef0d7bdec2d7981a6a3d4249bf0e6aab60634b72ad02c2b8023a9`. BEST was not moved.

Decision thresholds are `BLOCKED_PENDING_OPERATOR_AUTHORIZATION`. SELECT-003 numeric floors do not transfer. The prepared preservation metric names are `unbind_clean_exact`, `classification_accuracy`, and `observed_label_accuracy`. Those names have no active numeric thresholds.

Admission-only parity passed. Preflight and the trainer entrypoint, both under `HYPERLEX_ALLOW_TRAIN=1` with `HLX_ADMISSION_ONLY=1`, share environment hash `759c591151c88074973c3ba2a555be551d3460c04c8cedf59ab36624de215885`. `admission_result` is `ADMISSION_PASS`. Status is `PREREGISTERED`. `optimizer_loaded` is false. Epochs 0. Gradient steps 0. The SELECT-004 output directory was absent before and after. `HLX_ADMISSION_ONLY` is excluded from the environment hash.

`TRAINING_READY` exists only when all three are true: the scientific contract is sealed, the decision rule is sealed, and real entrypoint admission passes. SELECT-004 stays below `TRAINING_READY` until a fresh threshold authorization for this experiment id. `training_launch_authorized` is false.

Representation completeness is `PASS`. Evaluation quality is `LIMITED`. Classification support is 188 rights-cleared non-none identities. Clean unbind is 250 identities, 125 targets, 2 role-scheme surfaces per target, from Princeton WordNet 3.0 only. Unsupported families remain relationship-dating, conflict-aggression, sports-competition, fashion-aesthetic, regional-cultural, and spiritual-mystic. A later result must not claim those families. Label universe sha256 `227b782011aad7e693fde253e103a24b3ca0bd6b04e090d446656fa943bf0175`. Absent-class policy `omit_when_gold_support_is_zero`.

Vendor calls: 0. Do not train. The next decision is a fresh SELECT-004 threshold authorization.
## SELECT-004 thresholds authorized — HLX-EXP-2026-09-26-SELECT-004

Fresh operator authorization for `HLX-EXP-2026-09-26-SELECT-004` only. It does not inherit authority from SELECT-001, SELECT-002, or SELECT-003. The sealed preregistration bytes stay `365f7ce7141e8ee899fc52d85584a32c21ecfcb596e316b1438463bd8db85c4a`.

`PROMOTE` requires `classify_macro_f1_nonnone` strictly greater than `seed-morph78` on the sealed twelve-class universe, sha256 `227b782011aad7e693fde253e103a24b3ca0bd6b04e090d446656fa943bf0175`, absent-class policy `omit_when_gold_support_is_zero`. Equality does not promote. The new SELECT-004 preservation floors are unbind clean exact within 0.01 on 250 identities, classification accuracy within 0.02 on 241 identities, and OBSERVED-label accuracy within 0.05 on 123 identities. A primary decrease, a preservation breach, or a hard integrity failure is `REJECT`. Equal primary metrics with every guard passing are `INCONCLUSIVE`. An inconclusive result is not resolved by changing thresholds.

Authorization artifact sha256 `7389783b52a5d5cf14ceca874cc12351d3f6571b6be8a8666c2040be38972625`. Post-authorization admission used `HYPERLEX_ALLOW_TRAIN=1` and `HLX_ADMISSION_ONLY=1`. Preflight and the trainer entrypoint share environment hash `a2b18512be8329ee63ad06e98f894c6138cf7eac05f6e82d53d4132e99a27f5d`. `admission_result` is `ADMISSION_PASS`. Status is `TRAINING_READY` because the scientific contract is sealed, the decision rule is sealed, and the real entrypoint passed. `optimizer_loaded` is false. Epochs 0. Gradient steps 0. Training was not started. Output directory stayed absent. BEST sha256 `fc53676bd347cccd4d0ac9a429f3469c36436f8eb0e09954e0c347c7b133a4a1` was not moved. Trunk sha256 `340ac08b74eef0d7bdec2d7981a6a3d4249bf0e6aab60634b72ad02c2b8023a9`. `training_launch_authorized` is false. `HLX_ALLOW_NO_HOLDOUT` stayed unset.

Representation completeness is `PASS`. Evaluation quality is `LIMITED`. The decision covers classify 241, classify_observed 123, classify_non_none 188, and unbind_clean 250. It does not establish performance for relationship-dating, conflict-aggression, sports-competition, fashion-aesthetic, regional-cultural, or spiritual-mystic. Clean unbind stays limited to the sealed WordNet slice. Vendor calls: 0. Do not train. The next decision is launch authorization only.
