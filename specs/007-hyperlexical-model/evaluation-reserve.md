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

A sealed reserve binding satisfies the holdout requirement when the active reserve is `EVAL_RESERVE` for the current experiment, all four slices are present on that active set, the binding digest matches the full `events.jsonl`, and training overlap by row id and by normalized text hash is 0 against that active set. Overlap rejects the run. It does not drop training rows. `HLX_HOLDOUT_MANIFESTS` is not a second requirement. `HLX_ALLOW_NO_HOLDOUT` does not admit a controlled experiment. Legacy launches that are not controlled experiments still use the manifest gate.

Active membership is the derived lifecycle `EVAL_RESERVE` whose experiment binding is only the current experiment. `evaluation_reserved` stays historical evidence and is not cleared when the lifecycle is `EVAL_SPENT`. Spent identities do not count, do not satisfy overlap, and cannot be reserved again. A ledger with no active identities is a missing active reserve. A live `EVAL_RESERVE` bound to another experiment does not satisfy the current experiment. Slice counts and the binding identity count use the active set. The events digest still covers the append-only log.

The default scientific variable remains `HLX_SELECT_METRIC`: that key is the only allowed difference. `HLX_SCIENTIFIC_VARIABLE=train_schedule`, set to the same value on the baseline, the candidate, and the process, is the only composite. It normalizes `HYPERLEX_TRAIN_EPOCHS`, `HYPERLEX_EARLY_STOP`, `HYPERLEX_EARLY_STOP_PATIENCE`, and `HYPERLEX_EARLY_STOP_MIN_EPOCHS` into one variable. Both arms must set `HLX_SELECT_METRIC=classify_macro_f1_nonnone`. Any other difference fails. An undeclared schedule difference fails. A selection-metric difference is not part of `train_schedule`. Declaring the variable does not register or authorize an experiment.

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

## SELECT-004 scored — HLX-EXP-2026-09-26-SELECT-004

One run finished under the sealed contract. Container `hlx-train-select004-1790448703` exited 0 after 40 epochs. The training schedule was not shortened. Checkpoint selection used `classify_macro_f1_nonnone` on the training-export validation surface. The selected checkpoint is epoch 3 at 0.64448782942204. Epoch 39 scored 0.5864567286803334. Candidate weights sha256 `9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6`. Consumed export sha256 `64b7d3dede25047cb6dd2e5b663f7fa72946ec82ac1a8816ae34622d1aaac430`, 9150 rows, reserve filter removed 0. The reserve ledger was not modified during training.

Reserve scoring used the sealed twelve-family universe `227b782011aad7e693fde253e103a24b3ca0bd6b04e090d446656fa943bf0175`. seed-morph78 macro-F1 0.022395727019119547, accuracy 0.14107883817427386, OBSERVED accuracy 0.032520325203252036, unbind clean exact 0.092. The candidate macro-F1 0.07245710784313726, accuracy 0.15767634854771784, OBSERVED accuracy 0.08130081300813008, unbind clean exact 0.100. Deltas are +0.05006138082401771, +0.01659751037344398, +0.048780487804878044, and +0.008. The char 3–5 baseline macro-F1 was 0.0, so CHAR_WINS did not occur. Decision **PROMOTE**. State `PROMOTION_ELIGIBLE`. `--apply-best` was not run. BEST remains `seed-morph78` / `fc53676bd347cccd4d0ac9a429f3469c36436f8eb0e09954e0c347c7b133a4a1`.

Representation completeness is `PASS`. Evaluation quality is `LIMITED`. The production head still emits the nine training families, so nine of the twelve gold families cannot be named and pull the absolute macro-F1 down for both checkpoints. The claim stays inside the sealed slices. Vendor calls: 0. The 40-epoch schedule was left as sealed. A later duration study can measure best-epoch locations; it is not a change to this result.

## SELECT-004 promoted — HLX-EXP-2026-09-26-SELECT-004

Operator authorization applied the selected epoch-3 checkpoint as BEST. The promoted object is `hyperlex-encoder-modernbert-base-seed-select004/model.safetensors`, sha256 `9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6`. `model.final.safetensors` (`d5be46be6611e382d837bab8868bb373cbead4f9caa3a666ca06f2b2cda1925b`) was not promoted. Epoch 39 was not promoted. No training ran. The reserve was not rescored.

Previous BEST `hyperlex-encoder-modernbert-base-seed-morph78` remains in place, sha256 `fc53676bd347cccd4d0ac9a429f3469c36436f8eb0e09954e0c347c7b133a4a1`.

Decision receipt sha256 `ee493b7d73b5e00ae27ec681bb52405bbcf2983a16a0297edad225aec52b7225`. Decision `PROMOTE`. Selection metric `classify_macro_f1_nonnone` `0.64448782942204`. Primary macro-F1 baseline `0.022395727019119547`, candidate `0.07245710784313726`, delta `0.05006138082401771`. Preservation deltas: classification accuracy `0.01659751037344398`, OBSERVED accuracy `0.048780487804878044`, unbind clean exact `0.008`. CHAR_WINS did not occur. Integrity `PASS`.

The 491 sealed reserve identities moved `EVAL_RESERVE` to `EVAL_BOUND` to `EVAL_SPENT` through `IdentityLedger.transition` and `persist_append`. Events sha256 before `8223ae11bb42bd1a98ebcd739d1cfbc470085e241826b662703faefdfe752da6`, after `96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c`. Projection sha256 before `d071b7aec8154203ce7f9ae9531639b8d638f86c2ac0c3af38bead9b3c4a48f9`, after `77e22433203879b252f7a9e309d2013d7550101d1c4a014b494d2c96df87d0e0`. The sealed binding file `c16e69559dd6582f687532ce6e2a2e9b52a70db1aa066d11e7e68e723936b371` was not rewritten. Historical consumed, spent, and abandoned identities outside this reserve were not changed.

Representation completeness is `PASS`. Evaluation quality is `LIMITED`. This promotion does not establish performance across the eighteen-family ontology. The production head cannot name nine of the twelve sealed gold families. That limitation is separate from the checkpoint pointer. Vendor calls: 0. No further experiment was started.

Promotion receipt sha256 `2e1f84b476f7355e31380419afad00d0b16d372235a0da6be85adc17fcf92d01`.

## SELECT-005 blocked — HLX-EXP-2026-09-27-SELECT-005

`HLX-EXP-2026-09-27-SELECT-005` is the next unclaimed experiment id. Claimed ids are `HLX-EXP-2026-09-26-SELECT-001` through `HLX-EXP-2026-09-26-SELECT-004`. This id is recorded and not sealed. No preregistration file, arm directory, reserve, or admission receipt was created.

`TRAINING_BLOCKED`. The proposed variable is the composite `train_schedule`. Control would be `max_epochs=40`, early stopping disabled, restore best. Candidate would be `max_epochs=12`, `minimum_epochs=4` scored epochs through epoch index 3, `early_stopping_patience=4`, strict increase, ties keep the earlier checkpoint, restore best. Both arms would pin `classify_macro_f1_nonnone`, warm start `hyperlex-encoder-modernbert-base-seed-morph65`, and export sha256 `64b7d3dede25047cb6dd2e5b663f7fa72946ec82ac1a8816ae34622d1aaac430` at 9150 rows.

The canonical trainer does not implement that candidate. `scripts/shadow/hyperlexical/loop.py` scores `for ep in range(epochs)` and never stops early. `score_now > best_macro` already keeps the earlier checkpoint on ties, and best weights are written back after the loop when the selection metric is `classify_macro_f1_nonnone`. `epoch-progress.jsonl` records the metric and not wall-clock. Spark and public `main` have the same `loop.py` sha256 `f51e7aaff69e9033cc9ba16eee7225bfeefcf521e32236bdb791cc7900e130a5`. Spark HEAD `098ece4d9e8ebb27b0b0d3410b1280ed072d4847` was clean. Public `main` is `2f73f30010cc16ee014ed8d88de73131eb80d0a9`.

The smallest separate change is an optional break in that epoch loop, default off: after a scored epoch, stop when at least 4 epochs have been scored and `epoch - best_epoch >= 4`, still capped by `max_epochs`, and append per-epoch wall-clock seconds to `epoch-progress.jsonl`. Setting `HYPERLEX_TRAIN_EPOCHS=12` is not that schedule. This record does not apply the change.

SELECT-004 artifacts were not modified. Its reserve stays `EVAL_SPENT` and was not reused. No new reserve was allocated. BEST was not moved. It still names `hyperlex-encoder-modernbert-base-seed-select004`, weights sha256 `9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6`. No optimizer was constructed. Epochs and gradient steps for this id are zero. Launch is not authorized.

## SELECT-005 still blocked — trainer synced, admission refused

Spark now carries public `main` `a7d254e8981695072f5be36ab7ebdcc46cbd672c` for the trainer. `scripts/shadow/hyperlexical/loop.py` sha256 `1aa395081d7709be3844bf2568d12100d73d931ecbc51af43c3d6e01dba77e2a`. Early stopping remains default-off. `HLX-EXP-2026-09-27-SELECT-005` is still not sealed. No preregistration file, arm directory, reserve, or admission receipt was created. The private ledger sections above were not replaced by the public projection.

`TRAINING_BLOCKED`. The trainer can express the candidate schedule. Canonical admission cannot seal it.

`admit_training_run` allows exactly one scientific difference, and that difference must be `HLX_SELECT_METRIC`. A non-mutating probe pinned both arms to `classify_macro_f1_nonnone` and changed only `HYPERLEX_TRAIN_EPOCHS` (`40` versus `12`) and `HYPERLEX_EARLY_STOP` (`0` versus `1`). Patience and minimum epochs were the same on both arms. The gate `single_variable` failed: `scientific variable count is 2: HYPERLEX_EARLY_STOP,HYPERLEX_TRAIN_EPOCHS`.

The spent ledger cannot supply a new `EVAL_RESERVE`. Events sha256 remains `96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c`. Live reserve counts are classify 0, classify_observed 0, classify_non_none 0, unbind_clean 0. The same probe failed at `holdout_reserve`: `reserve slice classify is absent`. The reserve scan also includes every identity with `evaluation_reserved` set. That scan is 491 identities, all derived `EVAL_SPENT`. A new reserve written onto this ledger would still fail that lifecycle check. The flag was not cleared. The SELECT-004 reserve was not reused.

No optimizer was constructed. Epochs and gradient steps for this id are zero. BEST was not moved. It still names `hyperlex-encoder-modernbert-base-seed-select004`, weights sha256 `9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6`. Launch is not authorized.

The smallest separate change is an admission-contract patch: accept one declared schedule variable while both arms share `classify_macro_f1_nonnone`, and treat historical `EVAL_SPENT` identities as outside the current reserve without clearing `evaluation_reserved`. Do not allocate a reserve before that contract exists.


## SELECT-005 still unsealed — admission contract synced, fresh reserve unavailable

Public `main` is `fab0de03d75e3280dc34feed425c4783ccf7e2b5`, the squash merge of the admission contract. Spark carries that `admission.py` sha256 `6ae7b63ca1b6e0459d9b795c731668b3eff524269d81bcb92181c0c9d407ab78` and `identity_ledger.py` sha256 `ac49b7240a895952b99b3ef9046f7a8185c8647badac7a45c8640d592057d1c5`. `scripts/shadow/hyperlexical/loop.py` remains sha256 `1aa395081d7709be3844bf2568d12100d73d931ecbc51af43c3d6e01dba77e2a`. The private ledger file was not replaced.

`HLX-EXP-2026-09-27-SELECT-005` is still not sealed. No preregistration file, arm directory, reserve binding, or admission receipt was created. The ledger was not appended. Events sha256 remains `96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c`. `evaluation_reserved` was not cleared. The SELECT-004 reserve stays `EVAL_SPENT` and was not reused.

A fresh reserve needs all four slices from text that is absent from the ledger and from the pinned export. The ledger has no `EVAL_RESERVE`, `EVAL_BOUND`, or `AVAILABLE` identities. The remaining settled hashes from the held-out stream that are absent from the ledger are `UNRESOLVED`, `NONE`, `RECLASSIFY`, or `ACCEPT` with `RIGHTS_UNRESOLVED`. Unresolved-rights rows stay out of `EVAL_RESERVE`. No novel rights-cleared classify settlement remains. A classify-absent reserve was not written. The WordNet unbind source was not admitted by itself.

No optimizer was constructed. Epochs and gradient steps for this id are zero. BEST was not moved. It still names `hyperlex-encoder-modernbert-base-seed-select004`, weights sha256 `9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6`. Launch is not authorized.


## SELECT-005 census — fresh reserve still unavailable

A second join of the 339 settlement events to the 7964 ledger identities found no novel rights-cleared classify row. Events sha256 remains `96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c`. The ledger was not appended. `evaluation_reserved` was not cleared. The SELECT-004 reserve was not reused.

All 6761 unique hashes in the pinned export are already in the ledger. Of the 98 settlement events absent from the ledger, none are in that export. Those 98 are 82 `UNRESOLVED` with cleared rights, 2 `UNRESOLVED` with unresolved rights, 7 `ACCEPT` with unresolved rights, 6 `NONE` with unresolved rights, and 1 `RECLASSIFY` with unresolved rights. `UNRESOLVED` means the operator reviewed the row and declined to settle it. Unresolved-rights rows stay out of `EVAL_RESERVE`. There are 0 novel `CC-BY-SA` rows with decision `ACCEPT`, `RECLASSIFY`, or `NONE`.

The 28 promoted-accept files are training gold under an older family set and were not remapped. WordNet can still supply `unbind_clean` and was not admitted alone, because a classify-absent reserve fails the slice gate. No preregistration, arm directory, reserve binding, or admission receipt was created. The optimizer was not constructed. Epochs and gradient steps for `HLX-EXP-2026-09-27-SELECT-005` remain 0. `training_launch_authorized` is false. BEST was not moved.


## SELECT-005 classify candidates blocked — HLX-EVAL-REVIEW-2026-09-27-001

Admission requires each active slice count to be at least 1. The classify floors are classify 1, classify_observed 1, and classify_non_none 1. Planning targets 606, 287, and 604 are not that floor. This pass did not lower the floor.

Packet `HLX-EVAL-REVIEW-2026-09-27-001` is an operator-review packet, not a reserve. Ready rows: 0. Other screened rows: label unresolved 10, rights blocked 69, provenance blocked 4, cohort duplicate 1. Previously declined rights-cleared rows and unresolved-rights events were not reopened. WordNet and the older promoted-accept files were not used. No operator decision was written.

Events sha256 remains `96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c`. The ledger was not appended. `HLX-EXP-2026-09-27-SELECT-005` was not sealed. BEST was not moved.


## ai-native evaluation family — 2026-09-27

Public `main` is `ca9403efe8470d46566abbcd098640f07b33b759`. `ai-native` is taxonomy-active. `evaluation.enabled` stays false. The production head stays nine names. No row was settled. The ledger was not appended. Events sha256 remains `96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c`.

The review packet `HLX-EVAL-REVIEW-2026-09-27-001` now has 10 ready rows proposing `ai-native`. Their stored class stays `INFERRED`. `classify_observed` is still short by 1 until an operator attests `OBSERVED`. `HLX-EXP-2026-09-27-SELECT-005` is not sealed.


## Operator attested the ready rows observed

The operator attested `OBSERVED` on all 10 ready rows in packet `HLX-EVAL-REVIEW-2026-09-27-001`. The proposed family is `ai-native`. Rights-blocked, provenance-blocked, and duplicate rows were not attested. No `ACCEPT`, `RECLASSIFY`, or `NONE` was written. The ledger was not appended. Events sha256 remains `96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c`. `HLX-EXP-2026-09-27-SELECT-005` is not sealed.

## Unbind preview refused as slang — 2026-09-27

The operator reviewed the first 20 positional surfaces from the novel WordNet unbind pool. None are admitted as slang. Eighteen are refused. `give a damn` and `in one's birthday suit` are quarantined for provenance review. Slang, idiom, colloquialism, and profanity stay distinct. No `ACCEPT`, `REJECT`, `CORRECT_TARGET`, or `UNRESOLVED` was written to the unbind settlement log. The ledger was not appended. Events sha256 remains `96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c`. These rows are not classify gold and must not be trained as slang. `HLX-EXP-2026-09-27-SELECT-005` is not sealed. Disposition packet `HLX-EVAL-UNBIND-PREVIEW-2026-09-27-001`.

## Unbind preview roles — 2026-09-27

Slang classification and structure unbinding stay orthogonal. On the same 20-surface preview, the operator marked 7 high-value unbind candidates, 8 secondary candidates, and 5 rejects. The rejects are `beta vulgaris`, `gulf of oman`, `u. s. air force`, `department of the federal government`, and `court of assize and nisi prius`. The slang disposition is unchanged: none admitted, 18 refused, and `give a damn` plus `in one's birthday suit` quarantined as slang. No unbind settlement decision was written. The 15 candidates are not admitted. The ledger was not appended. Events sha256 remains `96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c`. `HLX-EXP-2026-09-27-SELECT-005` is not sealed. Packet `HLX-EVAL-UNBIND-PREVIEW-2026-09-27-001`.

## Unbind screen specified — 2026-09-27

`RUNE.UNBIND_SCREEN.v1` is a candidate-selection rule, not an admission filter. Specification agreement with the 20-item preview is 20/20. That figure is specification fit, not held-out precision. A held-out validation sample of 32 admissible positional surfaces, excluding those 20, is recorded with proposed buckets and `gold` null. Provisional screen counts on 63882 admissible positional surfaces are high-value 1965, secondary 60559, reject 1358. Those counts are not a draw. No settlement was written. The ledger was not appended. Events sha256 remains `96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c`. `HLX-EXP-2026-09-27-SELECT-005` is not sealed. Packet `HLX-EVAL-UNBIND-SCREEN-2026-09-27-001`.

## Unbind screen v2 — 2026-09-27

`RUNE.UNBIND_SCREEN.v2` replaces the v1 proposal as the screening hypothesis. It is not authorized as the SELECT-005 screen. Surface patterns remain candidate-generation heuristics. Hard exclusions are proper name, titled entity, taxonomy, productive number, and unconstrained free composition. Agreement after the revision is 20/20 on the first preview and 32/32 on the reviewed sample. That agreement is fit, not held-out precision. A new validation sample excludes all 52 reviewed surfaces and carries `gold` null. No settlement was written. The ledger was not appended. Events sha256 remains `96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c`. `HLX-EXP-2026-09-27-SELECT-005` is not sealed. Packet `HLX-EVAL-UNBIND-SCREEN-2026-09-27-002`.

## Unbind screen v3 — 2026-09-27

`RUNE.UNBIND_SCREEN.v3` is a hypothesis. It is not authorized as the SELECT-005 screen. Candidate-generation patterns do not assign high-value. The automatic screen emits reject or unresolved only. v2 pool counts stay frozen at high-value 1977, secondary 55427, reject 6478, over 63882 positional surfaces, and were not recomputed. No settlement was written. The ledger was not appended. Events sha256 remains `96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c`. `HLX-EXP-2026-09-27-SELECT-005` is not sealed. Packet `HLX-EVAL-UNBIND-SCREEN-2026-09-27-003`.

## Unbind screen v3 held out — 2026-09-27

`RUNE.UNBIND_SCREEN.v3` stays a proposed refinement. Fifty-two surfaces are frozen as development data and thirty-two as validation-development data. Agreement on those eighty-four is fit, not held-out precision. A fresh sample of 29 admissible positional surfaces excludes all 84. Predictions were not hand-corrected. Held-out precision is not computed. v2 pool counts stay frozen at high-value 1977, secondary 55427, reject 6478, over 63882 positional surfaces. The v3 screen was not run on that pool. No settlement was written. The ledger was not appended. Events sha256 remains `96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c`. `HLX-EXP-2026-09-27-SELECT-005` is not sealed. Packet `HLX-EVAL-UNBIND-SCREEN-2026-09-27-004`.

## Unbind held-out frozen — 2026-09-27

The 29-row v3 application is frozen. Sample sha256 `8af5644061a7a60fc5620c217e15a4ec8145f170edee9d8ff4e2999e7b86605e`. It was produced by one application of `RUNE.UNBIND_SCREEN.v3` and was not hand-corrected. Operator labels are pending. Held-out precision is `NOT_COMPUTABLE`. v3 was not revised. Development data remain 52 rows. Validation-development data remain 32 rows. Admitted 0. Settled 0. Gold 0. The ledger was not appended. Events sha256 remains `96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c`. `HLX-EXP-2026-09-27-SELECT-005` is not authorized and is not sealed.

## Unbind screen evaluation lane — 2026-09-27

`HLX-EVAL-UNBIND-SCREEN-V3-001` evaluates the frozen 29-row v3 application. Source sample sha256 remains `8af5644061a7a60fc5620c217e15a4ec8145f170edee9d8ff4e2999e7b86605e`. Prediction, operator judgment, gold, admission, and settlement are separate artifacts. The blind review does not carry the predicted bucket. Operator labels are pending. Held-out precision and the confusion matrix are `NOT_COMPUTABLE`. A scored report does not authorize `HLX-EXP-2026-09-27-SELECT-005`. The ledger was not appended. Events sha256 remains `96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c`.

## Unbind screen held-out scored — 2026-09-27

Operator labels for HLX-EVAL-UNBIND-SCREEN-V3-001 are frozen. Label sha256 `4e7bae5986e6345de62086af270a1d1a6902103d69a50d8f0b1e4e0fe01ecde5`. The source sample sha256 remains `8af5644061a7a60fc5620c217e15a4ec8145f170edee9d8ff4e2999e7b86605e`. Resolved accuracy is 16/29. High precision is 1 and recall is 6/13. Secondary precision is 4/17 and recall is 1. Reject precision is 1 and recall is 6/12. Quarantine support is 0. Every error is false secondary: 7 operator-high and 6 operator-reject. False high and false reject are 0. revision_eligible stays false. SELECT-005 is not authorized. The ledger was not appended. Events sha256 remains `96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c`.

## Unbind screen v4 hypothesis — 2026-09-28

The v3 held-out score stays 16/29. All 13 errors are false secondary: 7 operator-high and 6 operator-reject. False high and false reject are 0. Those 29 rows are now v4 development evidence, not a validation set. `RUNE.UNBIND_SCREEN.v4` is drafted and not encoded, applied, or authorized. It would only add coverage around the secondary basin: normalized productive numbers, multi-token personal names, organization glosses, species common names, and medical technical phrases on one side; nonliteral and conventionalized gloss evidence on the other. Existing high and reject decisions stay in place. `revision_eligible` stays false. SELECT-005 is not authorized. The ledger was not appended. Events sha256 remains `96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c`.

## Unbind screen v4 acceptance frozen — 2026-09-28

`RUNE.UNBIND_SCREEN.v4.ACCEPTANCE` is frozen and the screen is not encoded. Acceptance sha256 `ffb39e38784a56ae15bae51718c61b78fc861e48399936dbed57fb7d0754c55b`. v4 may only move additional secondary fall-throughs, and only by semantic evidence classes. It must not reinterpret v3 high or reject logic, redefine secondary, or train on a future validation sample. Phrase-specific exceptions are prohibited. The 113 reviewed surfaces are the later regression set. The next measurement sample must exclude them and be frozen before inspection. `revision_eligible` stays false. SELECT-005 is not authorized. The v3 sample and label hashes are unchanged. The ledger was not appended. Events sha256 remains `96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c`.

## Unbind screen v4 encoded — 2026-09-28

`RUNE.UNBIND_SCREEN.v4` is encoded as a wrapper over a frozen v3 bucket. It inspects a row only when that bucket is secondary. Patch A may move secondary to reject. Patch B may move secondary to high. Existing high and reject decisions are not reopened. The acceptance contract is unchanged, sha256 `ffb39e38784a56ae15bae51718c61b78fc861e48399936dbed57fb7d0754c55b`.

The 113 reviewed surfaces were replayed as a regression suite. Gate A through Gate E passed. High rows unchanged: 39. Reject rows unchanged: 28. Secondary moves: 13 to high and 6 to reject. Each move has one Patch A or Patch B evidence code. No phrase-specific rule fired. Operator conflict on those moves: 0. This replay is not a new precision estimate.

Success criteria were frozen before the measurement draw, sha256 `4fcbebfad7797eb22393fa94a389f1ef41402612e359b63d3a3a4b031c6cf8be`. High and reject precision floors are the v3 held-out floors of 1. The false-secondary rate must be strictly below 13/29. False high and false reject are not allowed. Perfect accuracy is not required.

The measurement sample excludes all 113 reviewed surfaces and duplicate normalized lexical identities. It is stratified by source part of speech and token count, two rows from each occupied cell. Occupied cells produced 28 rows. Sample sha256 `dae8851134aa960a13e072ae017428054c68b988c8d7e6f86d8cab2d16c2586b`. v4 was applied once. Hand corrections are 0. Operator labels are absent. Precision is `NOT_COMPUTABLE`. `revision_eligible` stays false. `HLX-EXP-2026-09-27-SELECT-005` is not authorized. The ledger was not appended. Events sha256 remains `96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c`. The v3 sample sha256 `8af5644061a7a60fc5620c217e15a4ec8145f170edee9d8ff4e2999e7b86605e` and label sha256 `4e7bae5986e6345de62086af270a1d1a6902103d69a50d8f0b1e4e0fe01ecde5` are unchanged.

## Unbind screen v4 measurement scored — 2026-09-28

Operator labels for the 28-row v4 measurement sample are frozen. Label sha256 `023691f8349f0dda12c234691f235ae109289fcf9eab86ec20be1e23bfed9463`. The sample sha256 remains `dae8851134aa960a13e072ae017428054c68b988c8d7e6f86d8cab2d16c2586b`. The prediction sha256 remains `a854847e516fbcd37fbb221456e8caf8c420552795ac7fc6225960bb5434084f`. Labels were recorded at `2026-09-28T02:17:00Z`, after the sample freeze at `2026-09-28T01:07:34Z`. Hand corrections are 0. v4 was not applied again.

Resolved accuracy is 16/28. High precision is 1 (7/7) and recall is 7/13. Reject precision is 1 (5/5) and recall is 5/11. Secondary precision is 4/16 and recall is 4/4. Quarantine support is 0. False high is 0. False reject is 0. False secondary is 12/28, which is below the frozen floor of 13/29. Every error is a secondary fall-through. The pre-registered success criteria pass, so `revision_eligible` is true. `HLX-EXP-2026-09-27-SELECT-005` is not authorized. Admitted 0. Settled 0. Gold 0. The ledger was not appended. Events sha256 remains `96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c`.

## Unbind screen v5 hypothesis — 2026-09-28

The v4 measurement artifact and score receipt stay frozen. Sample sha256 `dae8851134aa960a13e072ae017428054c68b988c8d7e6f86d8cab2d16c2586b`. Prediction sha256 `a854847e516fbcd37fbb221456e8caf8c420552795ac7fc6225960bb5434084f`. Label sha256 `023691f8349f0dda12c234691f235ae109289fcf9eab86ec20be1e23bfed9463`. Acceptance sha256 `ffb39e38784a56ae15bae51718c61b78fc861e48399936dbed57fb7d0754c55b`. Resolved accuracy remains 16/28. High precision remains 1. Reject precision remains 1. False secondary remains 12/28. `revision_eligible` on that measurement remains true.

Those 28 rows are now v5 development evidence, not a validation set. Evidence sha256 `dcab832038c3209a54a4159b23caf4eecfb94864cef7188af28f1ae3b0ff80c0`. The twelve secondary fall-throughs are two escape routes only: referential or terminological rows that stayed secondary, and lexicalized noncompositional rows that stayed secondary. They are not a fit list.

`RUNE.UNBIND_SCREEN.v5` is drafted and not encoded, applied, or authorized. It is a wrapper over a frozen v4 bucket. It inspects a row only when that bucket is secondary. One referential/terminological dominance test may move secondary to reject. One lexicalized noncompositionality test may move secondary to high, and only when the surface is conventionalized and the gloss is not compositionally recoverable. A lexicalized and mostly compositional surface stays secondary. Existing high and reject decisions stay in place. A separate rule for each miss is prohibited. `HLX-EXP-2026-09-27-SELECT-005` is not authorized. Admitted 0. Settled 0. Gold 0. The ledger was not appended. Events sha256 remains `96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c`.
