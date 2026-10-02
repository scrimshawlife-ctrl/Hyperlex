# Changelog

## Unreleased

- **Rebase V6 on stronger pretrained semantic encoder (Spec 007):**
  Representation rebase around MPNet-class sentence embeddings. Freeze
  MPNet zero-shot witness REP≈0.206. MODEL_WIDE_BEST remains historical
  control (not mutated). Small encoder family (MPNet / BGE-base /
  MS MARCO), frozen heads, calibrated similarity, axis projections, PEFT
  adapter. Floors locked; QUAL sealed; no A–F carousel.

- **Reassess V6 task signal and pretrained representation (Spec 007):**
  Diagnostic phase after architecture bakeoff exhaustion. Freeze zero-shot
  CONTROL reference REP≈0.162. Axis/label audits, description
  adequacy/sensitivity/oracle, human-vs-model learnability, learning curves,
  frozen vs partial vs full fine-tune, probes, sentence/NLI pretrained
  comparison. No architecture-family bakeoff; floors locked; QUAL sealed.
  Key result: `all-mpnet-base-v2` read-only semantic matching REP **0.206**
  clears the 0.20 floor; NLI-DeBERTa 0.045; CONTROL ModernBERT 0.162.
  Learning curves `EARLY_SATURATION` under ModernBERT training. Disposition
  **`V6_TASK_SIGNAL_REASSESSMENT_COMPLETE`**. Primary diagnosis
  **`PRETRAINED_REPRESENTATION_MISMATCH`**. Receipt
  `classification-v6-task-signal-reassessment-receipt-20261001.json`
  (`8703b73d…`). Next: `REBASE_V6_ON_STRONGER_PRETRAINED_SEMANTIC_ENCODER`.

- **Continue V6 architecture bake-off — architecture reset (Spec 007):**
  After `V6_BAKEOFF_NO_ADVANCE` (REP macro-F1 ≈0.024), replace A/B/C retuning
  with tracks **D** (label-description NLI/cross-encoder), **E** (joint
  text–label embeddings), **F** (hierarchy-aware contrastive), plus CONTROL vs
  EXTERNAL encoder controls and a read-only zero-shot text↔label-description
  diagnostic. Floors locked (REP system ≥0.20, hierarchy viol ≤0.05, axis
  macro-F1 ≥0.10). QUAL sealed. Ontology/migration gold unchanged.
  Results: zero-shot best REP system macro-F1 **0.162** > trained D **0.134**
  > ABC **0.024**; no candidate advanced. Disposition
  **`V6_ARCHITECTURE_BAKEOFF_EXHAUSTED`**. Primary diagnosis
  **`LABEL_SEMANTICS_PRIOR_STRONGER_THAN_CURRENT_TRAINED_REPRESENTATION`**.
  Receipt `classification-v6-architecture-reset-bakeoff-receipt-20261001.json`
  (`e7264a0f…`). Next:
  `REASSESS_V6_TASK_SIGNAL_AND_PRETRAINED_REPRESENTATION`.

- **Rebuild V6 labels and run architecture bake-off (Spec 007):**
  Amended settlement protocol with three-level multi-label agreement
  (per-label / per-example Jaccard·set-F1 / boundary matrices + Wilson CIs);
  boundary-stratified top-up only for inconclusive strata. Deterministic
  TRAIN/DEV/REP migration to `domain_labels[]` / `function_labels[]` /
  `mediation_labels[]` / `ontology_uncertainty` (DIRECT 3707 / MULTI_LABEL
  307 / RULE_DERIVED 30 / HUMAN_RESETTLEMENT 386). QUAL remains sealed
  historical secondary. Controlled A/B/C bake-off under MODEL_WIDE_BEST as
  **control** (not assumed backbone). Selection repair: `0.0 or 1` falsely
  treated zero hierarchy violations as 1.0 and absolute REP macro-F1 (~0.02)
  was allowed to advance — now require min REP system macro-F1 0.20 +
  hierarchy violation ≤0.05. Disposition **`V6_BAKEOFF_NO_ADVANCE`**.
  Receipt `classification-v6-label-migration-bakeoff-receipt-20261001.json`
  (`b936b49b…`). Next: `CONTINUE_V6_ARCHITECTURE_BAKEOFF`.

- **Complete V6 human ontology settlement (Spec 007):**
  Dual independent text-only operator protocols on the 120-row sample
  (acquisition gold / model scores withheld). Structure remains
  `HIERARCHICAL_MULTI_LABEL`. Settlements: identity-affiliation
  **`CONTEXT_ONLY`** (not Stage-B gold); evaluative vs relational
  **`SEPARATE_COMPATIBLE_LABELS`**; gambling vs crypto
  **`SEPARATE_DOMAINS_WITH_STRICT_GAMBLING`** (wagering-only gambling).
  Freeze `HYPERLEX_V6_FAMILY_ONTOLOGY_V1_FINAL` + migration contract.
  TRAIN/DEV/REP: AUTO_MIGRATABLE 4166 / HUMAN_RESETTLEMENT 386 (bounded
  identity queue n=140; no auto-relabel this phase). QUAL uninspected;
  prefer new qualification surface. Geometry not used to decide.
  Disposition **`V6_ONTOLOGY_READY`**. Receipt
  `classification-v6-human-ontology-settlement-receipt-20261001.json`
  (`04a76503…`). No train. Next:
  `REBUILD_V6_DATA_LABELS_AND_DESIGN_MODEL_PHASE`.

- **Revise Hyperlex V6 ontology before modeling (Spec 007):**
  Freeze `HYPERLEX_V5_FAMILY_ONTOLOGY` as `HISTORICAL_RESEARCH_ONTOLOGY`.
  Semantic-level diagnosis: flat 18-way conflates DOMAIN × RELATION ×
  FUNCTION. Preferred lineage `HYPERLEX_V6_FAMILY_ONTOLOGY_V1` =
  **hierarchical multi-label** (10 domains + AI⊂technology child, 4
  functions, optional internet_register mediation; deprecate
  regional-cultural exclusive; identity-affiliation unresolved for human
  settlement). Stage-B task spec `HIERARCHICAL_MULTI_LABEL`. Support
  viability PASS on mapped TRAIN/DEV/REP; geometry validation still
  inadequate (margin within−between ≈ −0.150; purity ≈ 0.179) under noisy
  category-proxy gold. QUAL not inspected; consequence =
  human re-settlement / new surface later. Disposition
  **`V6_ONTOLOGY_BLOCKED_ON_HUMAN_AGREEMENT`**. Receipt
  `classification-v6-ontology-revision-receipt-20261001.json`
  (`9377d669…`). No train / encoder choice / retriever. Next:
  `COMPLETE_V6_HUMAN_ONTOLOGY_SETTLEMENT`.

- **Build representative V6 data foundation (Spec 007):**
  Freeze `HYPERLEX_V5_RESEARCH_BASELINE` (not release-qualified). Define
  `HYPERLEX_V6_OPERATING_DISTRIBUTION_V1`, independent
  TRAIN/DEV/REP_VAL/QUAL roles, gold-identifiability carry-forward, and
  preregistered Stage-A/B/system evaluation with dual validation reporting.
  NATURAL OBSERVED corpus settled after NONE top-up:
  TRAIN 2796 / DEV 506 / REP 1250 / QUAL 486 (100% OBSERVED+NATURAL;
  18 families; train max family share ≤6%). All section-22 volume gates
  true; disjointness vs spent history PASS; QUAL metadata sealed
  (`HYPERLEX_V6_QUALIFICATION_001`). Ontology audit
  **structurally broken** (152 review-required pairs); base representation
  `INADEQUATE`; retrieval `NOT_VIABLE`. Human agreement protocol + 120-row
  sample awaiting operator annotation. Disposition
  **`V6_DATA_FOUNDATION_PARTIAL`**. Receipt
  `classification-v6-data-foundation-receipt-20261001.json`
  (`8ea02186…`). No V6 train / no V5 retune / no architecture choice. Next:
  `REVISE_HYPERLEX_V6_ONTOLOGY_BEFORE_MODELING`.

- **Review V5 qualification failure at system level (Spec 007):**
  Read-only audit of `QUALIFICATION_FAIL` on spent surface
  `HYPERLEX_V5_PIPELINE_QUALIFICATION_001`. Finds
  **MATERIAL_DISTRIBUTION_SHIFT** (V1R2 paired/inferred vs fresh OBSERVED),
  Stage-A collapse with SHORT_ATOM NONE local success preserved
  (false_entry 0.0), Stage-B independent failure on A-correct PRESENT
  (fam_prec 0.275; ai-native attractor 42.6% index mass), ontology
  **NOT_RELIABLY_SEPARABLE** (between-centroid sim > within), threshold/
  floor counterfactuals **STRUCTURAL_OVERLAP** (no rescue). Diagnosis
  **`MIXED_SYSTEM_GENERALIZATION_FAILURE`**; disposition
  **`V5_RESEARCH_PROTOTYPE`**; surface
  `QUALIFICATION_SURFACE_HARD_BUT_VALID`. Rejects threshold/floor/matched-
  surface/index-enlarge/reserve/local-loss micro-fixes. Receipt
  `classification-v5-qualification-failure-system-review-receipt-20261001.json`
  (`6ba921e1…`). No train/retune/index rebuild/BEST move. Next:
  `BUILD_REPRESENTATIVE_V6_DATA_FOUNDATION`.

- **Qualify V5 pipeline on fresh evaluation surface (Spec 007):**
  `QUALIFY_HYPERLEX_V5_PIPELINE_ON_FRESH_EVALUATION_SURFACE` built a fresh
  text-identifiable surface (n=500; PRESENT 243 / NONE 203 / UNCERTAIN 54;
  15 families; OBSERVED 100%; SHORT_ATOM NONE 43; SHORT_ATOM PRESENT 0
  shortfall; domain-irrelevant unsupported), sealed it
  (`rows=7f7cd2a0…` / `seal=fec23f96…`), and one-shot scored the frozen
  V1R2 package (`STAGE_A_BEST=f2b00c5d…`, index `4febe96e…`, floors
  0.83/0.01, thr 0.60/0.75). Disjointness + identifiability PASS. Primary
  gates all miss: false_entry 0.315 / PRESENT recall 0.584 / NONE recall
  0.685 / fam_prec 0.123. Disposition **`QUALIFICATION_FAIL`**;
  `RELEASE_ELIGIBLE=false`; Hub unauthorized; all 500 identities
  `evaluation_spent=true`. Receipt
  `classification-v5-pipeline-qualification-receipt-20261001.json`
  (`88ed9fb5…`). No train/retune/index rebuild/reserve reuse. Next:
  `REVIEW_V5_QUALIFICATION_FAILURE_AT_SYSTEM_LEVEL` (do not reopen Stage A/B
  automatically).

- **Seal + package V5 Stage-A/B V1R2 pipeline (Spec 007):**
  `SEAL_AND_PACKAGE_HYPERLEX_V5_STAGE_A_B_V1R2_PIPELINE` freezes
  `HYPERLEX_V5_STAGE_A_B_PIPELINE_V1` on canonical Stage-A `f2b00c5d…` +
  V1R2 Stage-B index `4febe96e…` / floors 0.83/0.01 (thr 0.60/0.75).
  Cold-load pass; integration false_entry 0.03357 / fam_prec ~0.808 /
  selective ~0.936; gating pass; round-trip mismatch counts 0; stale audit
  pass. Package `HYPERLEX_V5_STAGE_A_B_V1R2_PACKAGE_V1`; Hub unpublished.
  States: Stage-A `CANONICAL_FROZEN`; Stage-B `CANONICAL_FOR_V1R2_PIPELINE`;
  Pipeline `CANONICAL_FROZEN`. Receipts
  `classification-v5-stage-a-b-v1r2-seal-package-receipt-20261001.json`
  (`0e468234…`), dependency manifest `c2d19bef…`. Reserve unscored. No
  train/retune/index rebuild. Next:
  `QUALIFY_HYPERLEX_V5_PIPELINE_ON_FRESH_EVALUATION_SURFACE`.

- **Align Stage-B to V1R2 under canonical Stage-A (Spec 007):**
  `ALIGN_V5_STAGE_B_TO_V1R2` rebuilds Stage-B index on identifiability-filtered
  V1R2 with factorized `STAGE_A_BEST=f2b00c5d…` embeddings and retunes floors on
  V1R2 validation only. `STAGE_B_V1R2_ALIGNMENT=APPLIED`. Index
  `4febe96e…` (n=948); floors 0.83/0.01; false_entry 0.03357; family_precision
  ~0.809; selective accuracy ~0.936; entry gating pass. Active Stage-B pins
  switched to V1R2 (`HLX-CLASSIFICATION-V5-STAGE-B-V1R2-001`); historical V1R9
  index `3fd6c87a…` / floors 0.64/0.07 retained. Stage-A not retrained;
  `MODEL_WIDE_BEST=9fba0f66…` unchanged; spent reserve unscored. Receipt
  `classification-v5-stage-b-v1r2-alignment-receipt-20261001.json`
  (`9f9c4355…`). Next:
  `SEAL_V5_STAGE_A_B_V1R2_PIPELINE_OR_SCOPED_PACKAGING`.

- **Evaluate full V5 pipeline + packaging (Spec 007):**
  `EVALUATE_FULL_V5_PIPELINE` ran factorized `STAGE_A_BEST=f2b00c5d…` against
  frozen Stage-B index `3fd6c87a…` / floors 0.64/0.07 on V1R9 validation
  (n=2051). Entry gating intact (NONE/UNCERTAIN never enter). Primary gate
  failed: false_entry 0.195 on V1R9 (Stage-A canonical is V1R2). Diagnosis
  `STAGE_A_V1R2_CANONICAL_ON_STAGE_B_V1R9_SURFACE` (+ index encoder parent
  mismatch vs superseded `cd2829c1…`). Production packaging contract sealed
  locally with `PACKAGING_READY=false`, Hub unpublished. Receipts
  `classification-v5-pipeline-eval-receipt-20261001.json` (`58568429…`),
  `classification-v5-pipeline-diagnosis-receipt-20261001.json` (`f3e7cabe…`),
  `classification-v5-production-packaging-receipt-20261001.json` (`86e6c490…`).
  Next: `ALIGN_V5_STAGE_B_TO_V1R2_OR_SCOPED_CROSS_SURFACE_EVAL`.

- **Freeze V5 Stage-A canonical + Stage-A/B pipeline (Spec 007):**
  Phase close: `HYPERLEX_V5_STAGE_A_CANONICAL_V1` binds `STAGE_A_BEST=f2b00c5d…`
  and `MODEL_WIDE_BEST=9fba0f66…` under factorized objective + V1R2
  identifiability contract (text-only, `AUTO_RELABEL=false`, thr 0.60/0.75).
  Serialization fail-closed for incomplete factorized heads. Stage-B parent pin
  updated to canonical Stage A; index `3fd6c87a…` and floors 0.64/0.07 frozen
  (`index_rebuilt=false`). Entry gating verified (NONE/UNCERTAIN never enter;
  PRESENT enters). Stale active references audited (live surface only). Pipeline
  `HYPERLEX_V5_STAGE_A_B_PIPELINE_V1` frozen.
  `V5_STAGE_A_STATE=CANONICAL_FROZEN`;
  `STAGE_A_RESEARCH_LOOP=CLOSED_FOR_CURRENT_FAILURE_CLASS`. Receipts
  `classification-v5-stage-a-canonical-receipt-20261001.json` (`11cd3502…`),
  `classification-v5-stage-a-b-pipeline-receipt-20261001.json` (`0842705f…`).
  Next phase: `EVALUATE_FULL_V5_PIPELINE_OR_PRODUCTION_PACKAGING`.

- **Retry promote ident-filtered factorized Stage-A candidate (Spec 007):**
  `RETRY_PROMOTE_STAGE_A_IDENT_FILTERED_FACTORIZED_CANDIDATE` promotes the
  complete REPRO-001 checkpoint `f2b00c5d…` (epoch 11, score 0.9673) to
  `STAGE_A_BEST`. Historical incomplete `8b2de447…` remains non-promotable.
  Preflight, cold-load (`n_keys=16`), V1R2 replay (false_entry 0.03357;
  PRESENT 0.951; NONE 0.965; SHORT_ATOM NONE FPR 0.01316), and round-trip
  logit parity (`decision_mismatch_count=0`) all pass. Thresholds stay
  0.60 / 0.75. `MODEL_WIDE_BEST` unchanged (`9fba0f66…`). Previous
  `STAGE_A_BEST` retained as `cd2829c1…` (`SUPERSEDED_STAGE_A_BEST`).
  Reserve remains `SPENT` / unscored. Receipt
  `classification-v5-stage-a-ident-filtered-factorized-repro-promotion-receipt-20261001.json`
  (`9541664c…`). Next:
  `FREEZE_V5_STAGE_A_CANONICAL_AND_UPDATE_DOWNSTREAM_PROVENANCE`.

- **Reproduce ident-filtered factorized train once (Spec 007):**
  `REPRODUCE_IDENT_FILTERED_FACTORIZED_TRAIN_ONCE` executes the single
  authorized REPRO-001 run from MODEL_WIDE_BEST on unchanged V1R2 under the
  sealed scientific contract + serializer fix. `SCIENTIFIC_RESULT=SETTLED_PASS`.
  `REPRODUCTION_CLASSIFICATION=SCIENTIFICALLY_EQUIVALENT_REPRODUCTION`.
  Selected complete checkpoint `f2b00c5d…` (epoch 11, score 0.9673); thresholds
  0.60 / 0.75; gates match original (false_entry 0.034; PRESENT 0.951; NONE
  0.965). SHORT_ATOM NONE relation FPR 0.0132 (prior unfiltered 0.539).
  Factorized heads cold-loadable (`n_keys=16`). Final complete checkpoint
  `b6b9ddfc…` retained. BEST / STAGE_A_BEST / V1R2 / reserve unchanged. Receipt
  `classification-v5-stage-a-ident-filtered-factorized-repro-train-once-receipt-20261001.json`
  (`8b8585a8…`). Next:
  `RETRY_PROMOTE_STAGE_A_IDENT_FILTERED_FACTORIZED_CANDIDATE`.

- **Authorize ident-filtered factorized reproduction train (Spec 007):**
  `AUTHORIZE_REPRODUCE_IDENT_FILTERED_FACTORIZED_TRAIN` binds
  `HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-REPRO-001`
  as a packaging-repair reproduction of parent `…-001` (`SETTLED_PASS`,
  selected encoder-only `8b2de447…`). Scientific inputs reused: V1R2
  `492ed367…`, annotations `95d54365…`, exclusion `661c9edb…`, class weights
  `13e8d0ca…` (literals verified, not recomputed), splits/identity hashes
  exact, objective/hparams/seed/gates unchanged.
  `SCIENTIFIC_CONFIG_PARITY=PASS`. Serializer fix `9edf8fc` is the only
  intended implementation delta; saves must
  `require_factorized_heads_in_flat`. RNG order verified from original
  runner (not byte-guaranteed). BEST / V1R2 / reserve unchanged.
  `TRAIN_AUTHORIZED=true` / `AUTHORIZED_NOT_STARTED` /
  `SCIENTIFIC_RESULT=NOT_COMPUTABLE`. Receipt
  `classification-v5-stage-a-ident-filtered-factorized-repro-authorize-receipt-20261001.json`
  (`09f3d456…`). Next:
  `REPRODUCE_IDENT_FILTERED_FACTORIZED_TRAIN_ONCE`.

- **Repair ident-filtered factorized checkpoint serialization — FAIL (Spec 007):**
  `REPAIR_IDENT_FILTERED_FACTORIZED_CHECKPOINT_SERIALIZATION` scanned retained
  selected-run artifacts for exact epoch-11 `relation_head` /
  `resolvability_head` tensors. `hit_count=0` (all safetensors encoder-only
  `8b2de447…`; no trainer state / export / live trainer). Sealed
  `REPAIR_NOT_POSSIBLE_WITHOUT_RETRAIN` without manufacturing a candidate.
  Whitelist permanently includes factorized heads; `require_factorized_heads_in_flat`
  + train-save asserts added; regression tests land. `STAGE_A_BEST` /
  MODEL_WIDE_BEST / V1R2 / thresholds / reserve unchanged.
  `SCIENTIFIC_RESULT=SETTLED_PASS` preserved (source = original settled run).
  Receipt
  `classification-v5-stage-a-ident-filtered-factorized-checkpoint-repair-receipt-20261001.json`
  (`6b041947…`). Next:
  `AUTHORIZE_REPRODUCE_IDENT_FILTERED_FACTORIZED_TRAIN`.

- **Promote ident-filtered factorized candidate — INVALID (Spec 007):**
  `PROMOTE_STAGE_A_IDENT_FILTERED_FACTORIZED_CANDIDATE` preflight passes on
  sealed SETTLED_PASS pins, but cold-load of selected `8b2de447…` fails closed:
  checkpoint is encoder-only (`relation_head`/`resolvability_head` dropped by
  `flatten_weight_tensors` whitelist at train save). `STAGE_A_BEST` remains
  `cd2829c1…`; MODEL_WIDE_BEST / V1R2 / reserve unchanged. Whitelist fixed for
  future saves. Receipt
  `classification-v5-stage-a-ident-filtered-factorized-promotion-receipt-20261001.json`
  (`1123d70d…`). Next:
  `REPAIR_IDENT_FILTERED_FACTORIZED_CHECKPOINT_SERIALIZATION`.

- **Train ident-filtered factorized once (Spec 007):**
  `TRAIN_STAGE_A_IDENT_FILTERED_FACTORIZED_ONCE` executes the single
  authorized fresh retrain from MODEL_WIDE_BEST on V1R2 under unchanged
  factorized objective. `SCIENTIFIC_RESULT=SETTLED_PASS`. Selected
  checkpoint `8b2de447…` (epoch 11, score 0.9673); thresholds
  relation 0.60 / resolvability 0.75; 100/100 grid pairs feasible.
  Gates: false_entry 0.034≤0.05; PRESENT recall 0.951≥0.70; NONE recall
  0.965≥0.90. SHORT_ATOM NONE relation FPR 0.013 (prior factorized 0.539).
  SHORT_ATOM PRESENT validation n=4 → `LOW_SUPPORT`. BEST / STAGE_A_BEST /
  V1R2 / spent reserve unchanged. Receipt
  `classification-v5-stage-a-ident-filtered-factorized-train-once-receipt-20261001.json`
  (`4a7d565c…`). Next:
  `PROMOTE_STAGE_A_IDENT_FILTERED_FACTORIZED_CANDIDATE`.

- **Authorize ident-filtered factorized train (Spec 007):**
  `AUTHORIZE_STAGE_A_IDENT_FILTERED_FACTORIZED_TRAIN` binds experiment
  `HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-001` to
  V1R2 `492ed367…`, annotations `95d54365…`, exclusion `661c9edb…`, objective
  `HYPERLEX_V5_STAGE_A_FACTORIZED_RELATION_OBJECTIVE_V1`. Parent splits
  preserved (train 2272 / val 848). Fresh train-only weights sealed
  (`13e8d0ca…`): relation ≈0.899/1.101; resolvability 1.703/0.50. Relation
  train eligible 2233 / masked 39. Fresh init from MODEL_WIDE_BEST;
  `TRAIN_AUTHORIZED=true` / `AUTHORIZED_NOT_STARTED`. Receipt
  `classification-v5-stage-a-ident-filtered-factorized-authorize-receipt-20261001.json`
  (`6341d083…`). Next: `TRAIN_STAGE_A_IDENT_FILTERED_FACTORIZED_ONCE`.

- **Apply gold identifiability filter → V1R2 (Spec 007):**
  `APPLY_GOLD_IDENTIFIABILITY_FILTER` emits membership-only surface
  `HYPERLEX_V5_STAGE_A_IDENTIFIABILITY_FILTERED_SURFACE_V1R2` from V1R1
  under contract `4ce0e5fa…`. Kept 3120 / excluded 465 (no auto-relabel).
  Labels: PRESENT 1215 / NONE 1851 / UNCERTAIN 54 (genuine textual only).
  Relation-loss eligible 3066; SHORT_ATOM PRESENT kept 11 / NONE 310.
  Dataset `492ed367…`; annotations `95d54365…`; exclusion manifest
  `661c9edb…`. `TRAIN_AUTHORIZED=false`. V1R1 / BEST / Stage-B / spent
  reserve unchanged. Receipt
  `classification-v5-stage-a-gold-identifiability-filter-receipt-20261001.json`
  (`e8e2ab7f…`). Next:
  `AUTHORIZE_STAGE_A_IDENT_FILTERED_FACTORIZED_TRAIN`.

- **Gold identifiability contract V1 (Spec 007):**
  `REVISE_GOLD_IDENTIFIABILITY_CONTRACT` freezes
  `HYPERLEX_STAGE_A_GOLD_IDENTIFIABILITY_CONTRACT_V1` with
  `MODEL_INPUT = text` only. Read-only V1R1 audit (3585 rows): 
  TEXT_IDENTIFIABLE 3066 / INVALID_GOLD 320 / CONTEXT_REQUIRED 145 /
  INSUFFICIENT_TEXT 54. SHORT_ATOM PRESENT: 315/326 context-dependent
  (invalid for text-only); only 11 remain relation-train admissible.
  All 1851 NONE are text-identifiable no-relation. AMBIGUOUS: 54 genuine
  textual uncertainty vs 145 missing annotation context. Recommended
  dispositions (not applied): KEEP_GOLD 3066 / EXCLUDE 465 /
  KEEP_FOR_RESOLVABILITY_ONLY 54. Hypothetical repaired surface viable
  (relation +/- 1215/1851). Primary repair
  `FILTER_CONTEXT_DEPENDENT_GOLD`; next (unauthorized)
  `APPLY_GOLD_IDENTIFIABILITY_FILTER`. No V1R1 mutation, auto-relabel,
  V1R2, input expansion, or BEST moves. Receipt
  `classification-v5-stage-a-gold-identifiability-contract-receipt-20261001.json`
  (`4ce0e5fa…`).

- **Diagnose factorized relation SETTLED_FAIL (Spec 007):**
  `DIAGNOSE_STAGE_A_FACTORIZED_RELATION_SETTLED_FAIL` (read-only) freezes
  cross-checkpoint SHORT_ATOM geometry on V1R1 for MODEL_WIDE_BEST /
  STAGE_A_BEST / two-stage fail `26841d5f…` / factorized fail `8a6981c1…`.
  Factorized vs two-stage embedding displacement ≈0.003 (objective change
  did not reshape label-separating geometry). No encoder layer reaches BA
  ≥0.70 (best layer 13 BA 0.657; last 0.570);
  `DEEPER_ADAPTATION_NOT_SUPPORTED`. Pooling/token paths do not recover
  (`POOLING_NOT_PRIMARY` / `TOKEN_SIGNAL_ABSENT`). ~49% of SHORT_ATOM val
  rows `REQUIRES_EXTERNAL_CONTEXT`; diagnostic subtype metadata lifts BA
  0.570→1.000 (not a production input). Primary:
  **`MODEL_INPUT_INFORMATION_DEFICIT`**; dataset consequence
  `GOLD_CONTRACT_REPAIR_REQUIRED`; next (unauthorized)
  `REVISE_GOLD_IDENTIFIABILITY_CONTRACT`. BEST pointers unchanged. Receipt
  `classification-v5-stage-a-factorized-relation-diagnose-receipt-20261001.json`
  (`827c0e2b…`).

- **Train factorized relation Stage-A once (Spec 007):**
  `TRAIN_STAGE_A_FACTORIZED_RELATION_ONCE` executes the single authorized
  fresh retrain
  (`HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-001`) from
  MODEL_WIDE_BEST on V1R1 + sealed factorized annotations. Selected epoch 12 /
  checkpoint `8a6981c1…` / selection score 0.8757. Threshold grid 100 pairs →
  **0 passing** → **`SETTLED_FAIL`** (false_entry 0.180 / NONE recall 0.807
  @ fail-display 0.50/0.50; PRESENT recall 0.888 passes). SHORT_ATOM relation
  FPR on NONE remains ~0.539 with PRESENT relation recall 0.75 — direct
  relation supervision did not jointly clear the diagnosed failure mode.
  STAGE_A_BEST / MODEL_WIDE_BEST unchanged; spent reserve unused. Receipt
  `classification-v5-stage-a-factorized-relation-train-once-receipt-20261001.json`
  (`76b1d5f5…`). Next:
  `DIAGNOSE_STAGE_A_FACTORIZED_RELATION_SETTLED_FAIL`.

- **Authorize factorized relation Stage-A train (Spec 007):**
  `AUTHORIZE_STAGE_A_FACTORIZED_RELATION_TRAIN` binds experiment
  `HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-001` to objective
  `HYPERLEX_V5_STAGE_A_FACTORIZED_RELATION_OBJECTIVE_V1`, V1R1
  `4095036e…`, annotations `4ac88450…`. Fresh train-only class weights
  sealed (`47e58773…`): relation eligible 2399 / masked 132; resolvability
  eligible 2531; final relation weights ≈0.954/1.046; resolvability
  1.531/0.50. Fresh init from MODEL_WIDE_BEST; STAGE_A_BEST untouched;
  spent reserve unused. `TRAIN_AUTHORIZED=true` /
  `AUTHORIZED_NOT_STARTED`. Receipt
  `classification-v5-stage-a-factorized-relation-authorize-receipt-20261001.json`
  (`133d8dd0…`). Next: `TRAIN_STAGE_A_FACTORIZED_RELATION_ONCE`.

- **Stage-A factorized relation objective V1 (Spec 007):**
  `SPEC_STAGE_A_FACTORIZED_OBJECTIVE` freezes
  `HYPERLEX_V5_STAGE_A_FACTORIZED_RELATION_OBJECTIVE_V1`. Gate1 target
  `POSSIBLE_EVIDENCE` deprecated as a training target; heads supervise
  `evidence_relation_present` and `semantic_resolvable` with deterministic
  final Stage-A decision. V1R1 sidecar derived without human relabel
  (3585 rows; relation+/-/masked 1535/1851/199; relation-loss eligible 3386).
  Architecture change not required. `TRAIN_AUTHORIZED=false`. Annotation
  SHA `4ac88450…`; receipt
  `classification-v5-stage-a-factorized-objective-receipt-20261001.json`
  (`45746d70…`). Next: `AUTHORIZE_STAGE_A_FACTORIZED_RELATION_TRAIN`
  (not authorized).

- **Stage-A semantic decomposition (Spec 007):**
  `STAGE_A_SEMANTIC_DECOMPOSITION` freezes the Gate1 target mismatch as
  conflation of domain relevance / evidence relation / semantic resolvability.
  V1R1 gold+subtype audit (3585 rows): all present NONE subtypes are
  domain-adjacent (`GENERIC_NONE=0`); `evidence_relation_present` and
  `semantic_resolvable` are directly/rule-derivable for the resolvable mass;
  UNCERTAIN notes already split four uncertainty causes but need not be
  re-settled to unblock. Primary decomposition
  **`RELATION_ONLY_DECOMPOSITION`** — single new primitive
  `evidence_relation_present` plus deterministic subtype/final-gold metadata;
  `NO_NEW_GOLD_REQUIRED`; dataset consequence `ANNOTATION_ONLY_CHANGE`;
  objective change justified; architecture change not justified. BEST/V1R1/
  reserve untouched; no train/V1R2. Receipt
  `classification-v5-stage-a-semantic-decomposition-receipt-20261001.json`
  (`93202898…`). Next: `SPEC_STAGE_A_FACTORIZED_OBJECTIVE` (not authorized).

- **Diagnose V1R1 generalization-retrain SETTLED_FAIL (Spec 007):**
  `DIAGNOSE_V5_STAGE_A_GENERALIZATION_RETRAIN_SETTLED_FAIL` read-only audit of
  failed candidate `26841d5f…` on V1R1. Gate1 FALSE_POSSIBLE dominated by
  SHORT_ATOM / length 1–4 / wiktionary / OBSERVED; SHORT_ATOM `p_possible`
  overlap 0.629; representation PARTIAL (centroid cosine 0.975); probes
  A/B/C do not separate SHORT_ATOM (BA≈0.61/0.61/0.57) →
  `REPRESENTATION_OR_SEMANTIC_FAILURE`. Semantic-core mass is
  LEXEME_ONLY+RELATION vs scarce EXPLICIT_EVIDENCE_CORE. Threshold class
  `STRUCTURAL_CLASS_OVERLAP`. Primary diagnosis
  **`GATE1_SEMANTIC_TARGET_MISMATCH`**; dataset change not justified;
  objective/semantic decomposition justified. BEST/V1R1/reserve untouched.
  Receipt
  `classification-v5-stage-a-generalization-retrain-diagnose-receipt-20261001.json`
  (`c6ae58c7…`). Next: `STAGE_A_SEMANTIC_DECOMPOSITION` (not authorized).

- **Train V1R1 two-stage Stage-A generalization once (Spec 007):**
  `TRAIN_V5_STAGE_A_TWO_STAGE_GENERALIZATION_ONCE` executes the single
  authorized fresh retrain
  (`HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-GENERALIZATION-001`) from
  MODEL_WIDE_BEST `9fba0f66…` on V1R1 (`4095036e…`); sealed weights
  `80b7f899…` / config `1527ae18…`. 12 epochs × 317 steps = 3804; selected
  epoch 12 / checkpoint `26841d5f…` / selection score 0.8976. Threshold grid
  100 pairs → **0 passing** → **`SETTLED_FAIL`** (false_entry 0.201 /
  NONE recall 0.784 @ fail-display 0.50/0.50; PRESENT recall 0.891 passes).
  SHORT_ATOM NONE false-entry remains ~0.546 while SHORT_ATOM PRESENT recall
  is 0.75 — matched-boundary repair did not jointly clear the observed
  failure mode. STAGE_A_BEST `cd2829c1…` / MODEL_WIDE_BEST unchanged; spent
  reserve unused; run limit exhausted. Receipt
  `classification-v5-stage-a-two-stage-generalization-train-once-receipt-20261001.json`
  (`35d9a706…`). Next:
  `DIAGNOSE_V5_STAGE_A_GENERALIZATION_RETRAIN_SETTLED_FAIL`.

- **Authorize V1R1 two-stage Stage-A generalization retrain (Spec 007):**
  `AUTHORIZE_V5_STAGE_A_TWO_STAGE_RETRAIN_ON_GENERALIZATION_SURFACE` seals
  new experiment `HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-GENERALIZATION-001`
  bound to architecture `631427cc…` + V1R1 dataset `4095036e…` / readiness
  `c4b5fc07…` / receipt `3dbdd9b2…`. Resolves Gate-1/Gate-2 class weights
  from train-only n=2531 (not V1R9 carry-forward) → artifact `80b7f899…`.
  Init policy: fresh retrain from MODEL_WIDE_BEST `9fba0f66…` + fresh heads
  (not STAGE_A_BEST `cd2829c1…` continuation). `TRAIN_AUTHORIZED=true` /
  `AUTHORIZED_NOT_STARTED` / `NOT_COMPUTABLE`; run limit 1. No train; V1R1
  unmutated; graph/Stage-B/BEST unchanged; spent reserve unused. Config
  `1527ae18…`; receipt
  `classification-v5-stage-a-two-stage-generalization-authorize-receipt-20261001.json`
  (`f7d4f3ad…`). Next: `TRAIN_V5_STAGE_A_TWO_STAGE_GENERALIZATION_ONCE`.

- **Remediate V5 Stage-A generalization surface → V1R1 (Spec 007):**
  `REMEDIATE_V5_STAGE_A_GENERALIZATION_SURFACE_GATES` seals successor
  `HYPERLEX_V5_STAGE_A_GENERALIZATION_SURFACE_V1R1`
  (`classification-v5-stage-a-generalization-surface-v1r1-20261001`,
  `4095036e…`). Retains all 2624 V1 rows; adds 961 fresh non-Wiktionary
  matched contrasts (remove 0). Clears SHORT_ATOM train floors, Wik share,
  bilateral domains, token ratio, top100 Jaccard, length/TF-IDF shortcuts →
  **`READY`**. Parent V1 unmutated; no train/retune/Stage-B/BEST moves;
  spent-reserve overlap 0. Receipt
  `classification-v5-stage-a-generalization-surface-v1r1-receipt-20261001.json`
  (`3dbdd9b2…`). Next:
  `AUTHORIZE_V5_STAGE_A_TWO_STAGE_RETRAIN_ON_GENERALIZATION_SURFACE`.

- **Build V5 Stage-A generalization surface v1 (Spec 007):**
  `BUILD_V5_STAGE_A_GENERALIZATION_SURFACE_V1` seals matched-boundary
  surface `classification-v5-stage-a-generalization-surface-v1-20261001`
  (`7567edcd…`; n=2624; train 1907 / val 717; PRESENT 1223 / NONE 1202 /
  UNCERTAIN 199; matched pairs 776). Critical SHORT_ATOM / DEFINITION_STYLE
  validation floors and pairing/provenance/disjointness/embedding-hardness /
  spent-reserve-overlap PASS. FAIL gates: SHORT_ATOM train floors,
  wiktionary_aggregate source share (~0.27), median token ratio 1.385,
  top100 Jaccard 0.235, length BA 0.621, TF-IDF BA 0.772, domain coverage
  gaps → **`PREREGISTERED`** (not READY). No train, no retune, no Stage-B
  mutation, no BEST moves, V1R9 unmutated. Receipt
  `classification-v5-stage-a-generalization-surface-receipt-20261001.json`
  (`424865ba…`). Next: `REMEDIATE_V5_STAGE_A_GENERALIZATION_SURFACE_GATES`
  (not retrain).

- **Preserve RESERVE_FAIL + diagnose V5 generalization (Spec 007):**
  `PRESERVE_RESERVE_FAIL_AND_DIAGNOSE_V5_GENERALIZATION` freezes
  `HYPERLEX_V5_PROMOTION_RESERVE_001=SPENT` / `RESERVE_FAIL` /
  production promotion REJECTED. Read-only val↔reserve decomposition under
  frozen STAGE_A_BEST `cd2829c1…` + Stage-B index `3fd6c87a…`. Stage-A
  false_entry +0.056 / PRESENT recall −0.334 / NONE recall −0.335; Stage-B
  emission precision on correctly admitted PRESENT remains ≥0.90.
  Diagnosis **`STAGE_A_GENERALIZATION_FAILURE`**; remediation
  **`NEW_STAGE_A_TRAINING_SURFACE`**. No retune, no index rebuild, no BEST
  moves, no reserve reuse. Receipt
  `classification-v5-reserve-fail-diagnose-receipt-20261001.json`
  (`823c985b…`).

- **Authorize/seal/score V5 promotion reserve (Spec 007):**
  `AUTHORIZE_SEAL_NEW_V5_RESERVE_THEN_ONE_SHOT_SCORE` creates
  **`HYPERLEX_V5_PROMOTION_RESERVE_001`** (n=250; NONE 61 / PRESENT 159 /
  UNCERTAIN 30; 15 families; OBSERVED 82.4%; disjoint PASS), then one-shot
  scores under frozen STAGE_A_BEST `cd2829c1…` + Stage-B index `3fd6c87a…`
  floors `0.64`/`0.07`. Primary false-entry `0.098` FAIL; family emission
  precision `0.667` FAIL → **`RESERVE_FAIL`**. Reserve identities
  `evaluation_spent=true`. BEST / STAGE_A_BEST unchanged; no retune; no
  production promotion. Receipt
  `classification-v5-promotion-reserve-receipt-20260930.json` (`2e083b9e…`).
  Next: `PRESERVE_RESERVE_FAIL` (offline diagnose; do not retune on spent
  reserve).

- **Wire V5 Stage-B behind STAGE_A_BEST (Spec 007):**
  `WIRE_V5_STAGE_B_RETRIEVAL_ON_STAGE_A_BEST` for
  `HLX-CLASSIFICATION-V5-STAGE-B-001` on V1R9 `8d4be830…`. Retrieval only on
  Stage-A `EVIDENCE_PRESENT` (UNCERTAIN abstains). Index `3fd6c87a…` from train
  POSITIVE_EVIDENCE (17 surface families). Calibrated floors score=`0.64` /
  margin=`0.07`. Primary false-entry `0.042` PASS; family emission precision
  `0.817` PASS → **`RESERVE_SEAL_AUTHORIZED`**. BEST / STAGE_A_BEST unchanged;
  no reserve created/scored. Receipt
  `classification-v5-stage-b-validation-receipt-20260930.json` (`51323ff4…`).
  Next: `AUTHORIZE_SEAL_NEW_V5_RESERVE_THEN_ONE_SHOT_SCORE`.

- **Promote two-stage Stage-A selected (Spec 007):**
  `PROMOTE_V5_STAGE_A_TWO_STAGE_SELECTED` applies component-scoped
  **`STAGE_A_BEST=cd2829c1…`** (epoch 11; Gate1=`0.75` / Gate2=`0.50`;
  architecture `HYPERLEX_V5_STAGE_A_TWO_STAGE_DECISION_GRAPH_V1`). Model-wide
  BEST `9fba0f66…` **UNCHANGED** (`BEST_MUTATED=false`). Canonical load:
  trunk→BEST→STAGE_A_BEST layers 20/21→gate heads. Flat runtime marked
  `DEPRECATED_FOR_CANONICAL_STAGE_A`. Stage-B entry:
  PRESENT→permit / NONE→stop / UNCERTAIN→ABSTAIN. Post-promotion replay exact
  parity (`fc601e69…`). Reserve unused. Receipt
  `classification-v5-stage-a-two-stage-promotion-receipt-20260930.json`
  (`d4c0cfd6…`). Next: `STOP_STAGE_A_ARCHITECTURE_WORK` (Stage-B integration).

- **Review two-stage Stage-A promotion (Spec 007):** read-only
  `REVIEW_V5_STAGE_A_TWO_STAGE_PROMOTION` on SELECTED `cd2829c1…` /
  epoch 11 / Gate1=`0.75` / Gate2=`0.50`. Settlement integrity **PASS**;
  cold-load replay (trunk→BEST→SELECTED overlay) exact parity
  (`replay_hash fc601e69…`); architecture identity PASS (Gate1/Gate2
  2-logit heads; no flat 3-way). Canonical inference frozen; OBSERVED/ATOM
  subgroup weaknesses recorded as `KNOWN_LIMITATION`. Recommend
  `STAGE_A_BEST` (do not overwrite model-wide BEST `9fba0f66…`). Reserve
  unused / not required by existing Stage-A policy.
  **`PROMOTION_READY`**; next `PROMOTE_V5_STAGE_A_TWO_STAGE_SELECTED`
  (not performed). Receipt
  `classification-v5-stage-a-two-stage-promotion-review-receipt-20260930.json`
  (`7e09c67d…`).

- **Train two-stage Stage-A once (Spec 007):** execute authorized
  `TRAIN_V5_STAGE_A_TWO_STAGE_ONCE` for
  `HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-001` on V1R9 `8d4be830…` /
  config `0117faca…` / weights `5496015a…`. Split witness `ecb88025…`
  (train 4437; Gate2 eligible 883). Restored epoch 11; SELECTED
  `cd2829c1…`; run receipt `9c358d2c…`. Threshold grid `n_passing=4`
  → **`SETTLED_PASS`** (false-entry `0.042`, PRESENT recall `0.705`,
  NONE recall `0.909`; macro-F1 `0.741`; UNCERTAIN recall `0.679`).
  Thresholds Gate1=`0.75` / Gate2=`0.50`. BEST unchanged; reserve unused;
  `promotion_candidate=true`. Receipt
  `classification-v5-stage-a-two-stage-train-once-receipt-20260930.json`.
  Next: human promote review (do not auto-move BEST).

- **Authorize two-stage Stage-A train (Spec 007):**
  `AUTHORIZE_V5_STAGE_A_TWO_STAGE_TRAIN_V1` pins experiment
  `HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-001` to architecture receipt
  `631427cc…`, V1R9 `8d4be830…`, BEST `9fba0f66…`. Hard pre-auth
  `RESOLVE_V5_TWO_STAGE_CLASS_WEIGHTS` sealed
  `TWO_STAGE_CLASS_WEIGHTS.json` (`5496015a…`) with literal Gate1
  NONE=0.7182 / POSSIBLE=1.2818 and Gate2 UNCERTAIN=1.1124 /
  CONFIRMED=0.8876. Training config `0117faca…`; authorization
  `c9b262de…`; `TRAIN_AUTHORIZED=true`,
  `TRAINING_STATUS=AUTHORIZED_NOT_STARTED`. No train / reserve / BEST /
  V1R9 mutation. Receipt
  `classification-v5-stage-a-two-stage-train-authorize-receipt-20260930.json`.
  Next: `TRAIN_V5_STAGE_A_TWO_STAGE_ONCE`.

- **Design freeze Stage-A two-stage decision graph (Spec 007):**
  `HYPERLEX_V5_STAGE_A_TWO_STAGE_DECISION_GRAPH_V1` freezes the B_TWO_STAGE
  redesign as spec only for experiment
  `HLX-CLASSIFICATION-V5-STAGE-A-005-TWO-STAGE` on V1R9 `8d4be830…`. Shared
  ModernBERT + Gate-1 (NONE vs POSSIBLE) + Gate-2 (UNCERTAIN vs CONFIRMED);
  `λ_gate2=1.0`; last 2 encoder layers; 10×10 threshold grid; checkpoint score
  `0.5×G1+0.5×G2` macro-F1; end-to-end gates unchanged. Flat head marked
  `DEPRECATED_FOR_V5_STAGE_A_CANONICAL_DECISION` (historical receipts retained).
  No train / authorize / reserve / BEST move (`9fba0f66…` UNCHANGED). Receipt
  `classification-v5-stage-a-two-stage-decision-graph-v1-receipt-20260930.json`
  (`631427cc…`). Next: `AUTHORIZE_V5_STAGE_A_TWO_STAGE_TRAIN_V1`.

- **Architecture/objective investigation Stage-A-004 / V1R9 (Spec 007):**
  read-only `ARCHITECTURE_OR_OBJECTIVE_INVESTIGATION` on SELECTED
  `82840630…` / dataset `8d4be830…`. Baseline
  DATA_INTEGRITY/LABEL_MAPPING/SURFACE_READY **PASS**. PRESENT FN n=263
  dominated by PRESENT→NONE / representation-failure modes; profile
  `CONFIDENT_NONE`; separability `PARTIALLY_SEPARABLE`; bottleneck `MIXED`.
  Focal already falsified; UNCERTAIN policy-invisible. Decision
  **`STAGE_A_ARCHITECTURE_REDESIGN_REQUIRED`**
  (`dataset_change_required=false`, `architecture_change_required=true`,
  `new_experiment_required=false`). Smallest reversible redesign (spec-only):
  `B_TWO_STAGE_DECISION_GRAPH`. No train/reserve/BEST/surface change. Receipt
  `classification-v5-stage-a-architecture-investigate-v1r9-receipt-20260930.json`
  (`7b16550c…`). Next: `DESIGN_V5_STAGE_A_ARCHITECTURE_REDESIGN_SPEC`.

- **Diagnose Stage-A-004 SETTLED_FAIL on V1R9 (Spec 007):** read-only
  `DIAGNOSE_V5_STAGE_A_SETTLED_FAIL` + matched-cohort
  `HYPERLEX_V5_STAGE_A_CONTROLLED_COMPARISON_V1` on SELECTED `82840630…` /
  dataset `8d4be830…`. False-entry already clears (need 0 fixes); binding
  gap is PRESENT recall (recover ≥72 FNs). Controlled coverage `0.126` →
  `INSUFFICIENT_MATCHED_SUPPORT`. Primary diagnosis
  `RESIDUAL_PRESENT_RECALL_FAILURE` (dataset change no; architecture
  investigation yes). No train/reserve/threshold/BEST. Receipt
  `classification-v5-stage-a-diagnose-v1r9-settled-fail-receipt-20260930.json`
  (`96871251…`). Next: `ARCHITECTURE_OR_OBJECTIVE_INVESTIGATION`.

- **Train Stage-A-004 once on V1R9 (Spec 007):** execute authorized
  `TRAIN_V5_STAGE_A_ONCE` for `HLX-CLASSIFICATION-V5-STAGE-A-004` on READY
  dataset `8d4be830…` / config `0c9df174…`. Restored epoch 12; SELECTED
  `82840630…`; run receipt `a03bc46a…`. Threshold grid `n_passing=0` →
  **`SETTLED_FAIL`**. PRESENT recall improved vs V1R8 parent
  (`0.527→0.587`; PRESENT→NONE 297→254) but still fails frozen 0.70 gate;
  false-entry `0.016` and NONE recall `0.983` pass. Gold-UNCERTAIN recall
  remains 0 under fail-display `P(PRESENT)`-only policy (162/162). Primary
  diagnosis `RESIDUAL_PRESENT_RECALL_FAILURE`. BEST unchanged; reserve
  unused; promotion_candidate=false. Receipt
  `classification-v5-stage-a-train-v1r9-once-receipt-20260930.json`.
  Next: `DIAGNOSE_V5_STAGE_A_SETTLED_FAIL`.

- **Authorize Stage-A-004 on V1R9 remediated surface (Spec 007):**
  `AUTHORIZE_V5_STAGE_A_NEXT_RUN_ON_REMEDIATED_SURFACE` pins experiment
  `HLX-CLASSIFICATION-V5-STAGE-A-004` to READY V1R9 dataset `8d4be830…`.
  Sealed GATE_EVAL `ff9cc665…` / READINESS `0b551c76…` digests (metadata
  only). Frozen training config `0c9df174…`; authorization receipt
  `7657092a…`. `TRAIN_AUTHORIZED=true`,
  `TRAINING_STATUS=AUTHORIZED_NOT_STARTED`. No train / reserve / BEST
  move (`9fba0f66…` UNCHANGED). Parent diagnosis
  `MIXED_UNCERTAIN_SURFACE_FAILURE`; V1R8 `c0fdd82d…` preserved. Receipt
  `classification-v5-stage-a-train-v1r9-authorize-receipt-20260930.json`.
  Next: `TRAIN_V5_STAGE_A_ONCE`.

- **Remediate Stage-A UNCERTAIN surface → V1R9 READY (Spec 007):**
  `REMEDIATE_V5_UNCERTAIN_SURFACE` replaces the narrow V1R8 UNCERTAIN bank
  without mutating V1R8 (`c0fdd82d…` preserved). New surface
  `HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R9` dataset
  `8d4be830…` (n=6488; train 4437 / val 2051). UNCERTAIN n=442 across all
  five frozen ambiguity reasons with OBSERVED share 0.704, PROSE-majority
  surface, and source-family caps ≤0.30/0.35. All original V5 readiness
  gates + UNCERTAIN-specific gates pass → **READY**. No train / reserve /
  BEST move / architecture change / checkpoint-driven acquire. Receipt
  `classification-v5-stage-a-uncertain-surface-remediate-receipt-20260930.json`.
  Next: `AUTHORIZE_V5_STAGE_A_NEXT_RUN_ON_REMEDIATED_SURFACE`.

- **Audit Stage-A UNCERTAIN label surface (Spec 007):** read-only
  `AUDIT_V5_UNCERTAIN_LABEL_SURFACE` on V1R8 / SELECTED `dba6d491…` with
  fail-closed MISSING_FIELD/NO_DATA/NOT_COMPUTABLE rules. Gold UNCERTAIN
  n=244 (train 183 / val 61) all `MULTIPLE_PLAUSIBLE_INTERPRETATIONS`; four
  other frozen reasons `NO_DATA`. Provenance/source isolated (INFERRED 234;
  ambiguous-source family). Boundary split PRESENT_LIKE 90 / NONE_LIKE 77 /
  CENTERED 77. GENUINELY_UNCERTAIN PRESENT FNs resemble PRESENT (no boundary
  conflict); NONE_DOMINATED FNs NONE-like. Diagnosis
  **`MIXED_UNCERTAIN_SURFACE_FAILURE`**. No train/relabel/reserve/BEST.
  Receipt `classification-v5-stage-a-uncertain-label-surface-audit-receipt-20260930.json`.
  Next: `REMEDIATE_V5_UNCERTAIN_SURFACE`.

- **Investigate Stage-A uncertain policy (Spec 007):** read-only score of
  Stage-A-003 SELECTED `dba6d491…` on V1R8. Freeze
  `HYPERLEX_V5_STAGE_A_GOLD_LABEL_MAPPING_V1` (dataset-semantic; admission
  PASS). UNCERTAIN head signal **PRESENT** (gold-UNC mean P(UNC)=0.55;
  top1-UNC 36/61) but scalar `P(PRESENT)`-only policy yields UNC recall 0.
  Native argmax restores UNC recall to 0.59 / macro-F1 0.687 but no frozen
  diagnostic policy (A–D) clears Stage-A gates (PRESENT stays ≤0.53;
  OBSERVED PRESENT ≤0.46). PRESENT FNs primarily `NONE_DOMINATED` (194/317).
  Diagnosis **`MIXED_UNCERTAIN_FAILURE`**. No train/threshold auth/reserve/BEST.
  Receipt `classification-v5-stage-a-uncertain-policy-investigate-receipt-20260930.json`.
  Next: `AUDIT_V5_UNCERTAIN_LABEL_SURFACE`.

- **Train Stage-A-003 focal loss once (Spec 007):** execute authorized
  `TRAIN_V5_STAGE_A_003_FOCAL_LOSS_ONCE` on V1R8 READY `c0fdd82d…` with
  frozen focal CE γ=2.0 / alpha=NONE / config `b8aad3ba…`. Restored epoch
  12; SELECTED `dba6d491…`; run receipt `1ca2e5d4…`. Threshold grid
  `n_passing=0` → **`SETTLED_FAIL`**. False-entry `0.0088` and ordinary
  NONE→PRESENT `8` (≤22) still pass; PRESENT recall `0.502` fails ≥0.70;
  PRESENT→NONE median P(NONE)=`0.904` remains confident-NONE.
  `H1_OBJECTIVE_LOSS_PRESSURE=FALSIFIED_FOR_FOCAL_INTERVENTION`.
  BEST/reserve unchanged; promotion_candidate=false. Receipt
  `classification-v5-stage-a-003-focal-loss-train-once-receipt-20260930.json`.
  Next: `INVESTIGATE_V5_STAGE_A_UNCERTAIN_POLICY`.

- **CLEAR audit: mixed-failure remediation already complete (Spec 007):**
  re-issued `REMEDIATE_V5_STAGE_A_MIXED_FAILURE` verified against sealed
  V1R8 READY `c0fdd82d…` / receipt `e61621af…` (12/12 gates). Parent
  V1R7 pins preserved; no V1R9 created. Ordinary wik aggregate 0.644 is a
  residual vs this CLEAR’s additional 0.35 target (not a frozen readiness
  gate). No train/reserve/BEST. Next remains authorized
  `TRAIN_V5_STAGE_A_003_FOCAL_LOSS_ONCE`.

- **Authorize Stage-A-003 focal objective (Spec 007):** freeze
  `HLX-CLASSIFICATION-V5-STAGE-A-003-FOCAL-LOSS` with `FOCAL_GAMMA=2.0`,
  `FOCAL_ALPHA_POLICY=NONE`, class/provenance weights unchanged from 002.
  Implementation tests A–F PASS; single-factor diff PASS (objective only).
  `FOCAL_LOSS_SPEC_SHA256=dce6dbf5…`, `TRAINING_CONFIG_SHA256=b8aad3ba…`,
  code `d58e078f…`. Objective FROZEN; train authorized once. Blocked
  preflight receipt preserved. No train; `decide_evidence` unchanged;
  BEST/reserve unchanged. Artifacts under
  `artifacts/experiments/HLX-CLASSIFICATION-V5-STAGE-A-003-FOCAL-LOSS/`.
  Next: `TRAIN_V5_STAGE_A_003_FOCAL_LOSS_ONCE`.

- **Stage-A-003 focal-loss blocked (Spec 007):** attempted
  `HLX-CLASSIFICATION-V5-STAGE-A-003-FOCAL-LOSS` after parent 002
  verification PASS. Parent pins match (specificity remediates; PRESENT
  recall 0.527; PRESENT→NONE median P(NONE)=0.994; n_passing=0). Training
  blocked: **`BLOCKED_UNFROZEN_OBJECTIVE`** — `FOCAL_GAMMA` / focal-loss
  semantics are not preregistered (parent forbids focal; investigation did
  not freeze a numeric gamma). No train, no invented gamma, no
  `decide_evidence` change, BEST/reserve unchanged. Receipt
  `classification-v5-stage-a-003-focal-loss-blocked-receipt-20260930.json`.
  Next: `AUTHORIZE_V5_STAGE_A_003_FOCAL_LOSS_OBJECTIVE`.

- **Architecture/objective investigation after V1R8 SETTLED_FAIL (Spec 007):**
  read-only verify→geometry→H1/H2/H3 on SELECTED `b22e9c20…` / V1R8
  `c0fdd82d…`. Specificity PASS; PRESENT recall FAIL; threshold grid
  `n_passing=0`. PRESENT→NONE profile **`CONFIDENT_NONE`** (74.7% deep NONE;
  near-boundary 1.0%) → threshold-only repair unsupported. H1 objective
  mismatch **SUPPORTED**; H2 hierarchical **PLAUSIBLE** (UNCERTAIN epistemic;
  decision ignores `P(UNCERTAIN)`); H3 head **NOT_SUPPORTED**; backbone change
  false. Selected single next change:
  `HLX-CLASSIFICATION-V5-STAGE-A-003-FOCAL-LOSS` (class-weighted focal CE only;
  V1R8/seed/backbone held). No train/dataset/reserve/BEST. Receipt
  `classification-v5-stage-a-architecture-investigate-receipt-20260930.json`.
  Next: `TRAIN_V5_STAGE_A_003_FOCAL_LOSS_ONCE`.

- **Train V5 Stage-A once on V1R8 (Spec 007):** execute authorized
  `TRAIN_V5_STAGE_A_ONCE` for `HLX-CLASSIFICATION-V5-STAGE-A-002` on READY
  dataset `c0fdd82d…` / config `2ce1b29b…`. Restored epoch 10; SELECTED
  `b22e9c20…`; run receipt `c0008f3c…`. Threshold grid `n_passing=0` →
  **`SETTLED_FAIL`**. False-entry improved to `0.012` (gate pass; ordinary
  false PRESENT 60→11) but PRESENT recall `0.527` (gate fail; worse than
  parent `0.648`). Primary diagnosis `RESIDUAL_PRESENT_RECALL_FAILURE`.
  BEST unchanged; reserve unused; promotion_candidate=false.
  Architecture investigation justified; no architecture change performed.
  Next: `ARCHITECTURE_OR_OBJECTIVE_INVESTIGATION`.

- **Authorize V5 Stage-A V1R8 train (Spec 007):** freeze recipe for
  experiment `HLX-CLASSIFICATION-V5-STAGE-A-002` on READY V1R8
  `c0fdd82d…`. Resolved config `2ce1b29b…`; authorization receipt
  `66a0b6f8…`; `train_authorized=true`. Isolated private auth dir; BEST
  unchanged. Next: `TRAIN_V5_STAGE_A_ONCE`.

- **Remediate V5 Stage-A mixed failure to READY (Spec 007):** execute
  `REMEDIATE_V5_STAGE_A_MIXED_FAILURE_V1` from parent V1R7 `a81ca68a…`
  under frozen `HYPERLEX_V5_STAGE_A_SURFACE_READINESS_GATES_V1`. Joint
  ordinary-NONE + PRESENT support repair: fresh Wiktionary/Wikipedia
  OBSERVED ordinary acquires (n=1013), train OBSERVED ordinary floor 160
  (was 0), train OBSERVED PRESENT floor 140 (was 80), Wikipedia source
  family diversification (`v5_src_wp_*`). Replacement surface V1R8
  dataset `c0fdd82d…` (train=4340 / validation=1950 / total=6290) passes
  all 12/12 mandatory gates → **READY**. Receipt `e61621af…`, gate_eval
  `73680e69…`. No train, reserve, architecture, threshold, or BEST move.
  Next: `TRAIN_V5_STAGE_A_ONCE`.

- **Diagnose V5 Stage-A SETTLED_FAIL (Spec 007):** read-only
  `DIAGNOSE_V5_STAGE_A_SETTLED_FAIL` + matched-cohort
  `HYPERLEX_V5_STAGE_A_CONTROLLED_COMPARISON_V1` on SELECTED `3b1b574a…`.
  False PRESENT mass is 95% ordinary-domain / 98% OBSERVED; controlled
  provenance coverage `0.418` → `INSUFFICIENT_MATCHED_SUPPORT`. Primary
  diagnosis `MIXED_STAGE_A_FAILURE` (dataset change yes; architecture no).
  Receipt `246bbae7…`. No train, reserve, threshold search, or BEST move.
  Next: `REMEDIATE_V5_STAGE_A_MIXED_FAILURE`.

- **Train V5 Stage-A once (Spec 007):** execute authorized
  `TRAIN_V5_STAGE_A_ONCE` for `HLX-CLASSIFICATION-V5-STAGE-A-001` on dataset
  `a81ca68a…` / config `4d2eaabd…`. Restored epoch 6; SELECTED checkpoint
  `3b1b574a…`; run receipt `b4299905…`. Threshold grid `n_passing=0` →
  **`SETTLED_FAIL`** (false-entry `0.069`, PRESENT recall `0.648`, NONE recall
  `0.929`). BEST unchanged; reserve unused; promotion_candidate=false.
  Retention: INITIAL/SELECTED/FINAL; intermediates pruned. Next:
  `DIAGNOSE_V5_STAGE_A_SETTLED_FAIL`.

- **Authorize V5 Stage-A train once (Spec 007):** freeze
  `HYPERLEX_CLASSIFICATION_V5_STAGE_A_TRAIN_V1` recipe +
  `HYPERLEX_V5_STAGE_A_LABEL_PROVENANCE_V1` for dataset `a81ca68a…` /
  BEST `9fba0f66…`. Experiment `HLX-CLASSIFICATION-V5-STAGE-A-001`;
  resolved config `4d2eaabd…`; authorization receipt `f736bf3d…`;
  `train_authorized=true`, `TRAINING_STATUS=AUTHORIZED_NOT_STARTED`.
  Label provenance sidecar valid for all 5877 rows (`invalid=0`). Does not
  train, does not modify the READY surface body, does not consume reserve,
  does not move BEST. Scientific result remains `NOT_COMPUTABLE`. Next:
  `TRAIN_V5_STAGE_A_ONCE`.

- **STOP before V5 Stage-A train-once (Spec 007):** input identity and READY
  surface verify (`a81ca68a…`, receipt `f07e4c04…`, gate_eval `0a4ad787…`,
  commit `fab24e4`, BEST `9fba0f66…`). Training did not start:
  `HYPERLEX_CLASSIFICATION_V5_STAGE_A_TRAIN_V1` freezes acceptance gates only;
  no canonical V5 `TRAIN_HYPERPARAMS` / train runner / resolved-config SHA, and
  `train_authorized` remains false. Scientific result `NOT_COMPUTABLE`. Next:
  `AUTHORIZE_V5_STAGE_A_TRAIN_V1` before one training execution.

- **Remediate v5 Stage-A surface to READY (Spec 007):** execute
  `REMEDIATE_V5_STAGE_A_SURFACE_V1` without changing frozen readiness
  thresholds. Replacement surface
  `HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R7` (n=5877;
  train=4489 / validation=1388; dataset `a81ca68a…`) passes all
  `HYPERLEX_V5_STAGE_A_SURFACE_READINESS_GATES_V1` simultaneously → **READY**.
  Parent failed surface `3add3aa6…` retained. No train, no reserve score, BEST
  unchanged. Next action: `TRAIN_V5_STAGE_A_ONCE` (`train_authorized` still
  false).

- **Freeze exact v5 surface readiness gates (Spec 007):** pin
  `HYPERLEX_V5_STAGE_A_SURFACE_READINESS_GATES_V1` (dataset floors, disjointness,
  duplicate quality with frozen near-dup method
  `hlx.v5.near_duplicate.normalized_jaccard_v1`, pairing, surface balance,
  lexical overlap minima, embedding hardness, shallow shortcuts, topic balance,
  provenance, schema integrity). Re-evaluate sealed surface
  `3add3aa6…` → **PREREGISTERED** (legacy READY superseded). Model acceptance
  gates remain separate (`false_entry≤0.05`, PRESENT≥0.70, NONE≥0.90). No train,
  no reserve score, BEST unchanged.

- **Design v5 Stage-A negative-evidence surface (Spec 007):** after v4
  `SETTLED_FAIL` / `STAGE_A_NONE_GENERALIZATION_FAILURE`, preregister
  `DESIGN_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE` and seal
  `HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1` (n=3116;
  train=2478 / validation=638) with ordinary-domain NONE priority and six NONE
  subtypes. Initial legacy readiness superseded by exact gate freeze above.
  No train, no reserve score, BEST unchanged.

- **Settle v4 balanced reserve FAIL (Spec 007):** seal ACQUIRE_READY pool
  (n=176) and one-shot score under frozen Stage A/B. Disposition
  `RESERVE_FAIL` (false-entry 0.4167 on n_none=48; emission 0.4545). No
  retune; BEST unchanged. Spent v4 identities marked `evaluation_spent`.

- **Seal v4 balanced reserve acquire READY (Spec 007):** after v3
  `RESERVE_FAIL` and zero AVAILABLE classify identities, preregister
  `HYPERLEX_CLASSIFICATION_V4_BALANCED_RESERVE_ACQUIRE_V1` floors
  (min_none≥40, min_present≥80, max family share≤0.20, ≥12 families), pin
  spent exclusions, and fetch Wiktionary OBSERVED rows. Disposition
  `ACQUIRE_READY` (n=176; none=48; present=128; 16 families; max share
  0.0625). No train, no reserve score, no threshold retune, BEST unchanged.

- **Settle v3 evidence gate FAIL (Spec 007):** seal fresh AVAILABLE reserve
  (n=109) and one-shot score under frozen Stage A/B thresholds. Disposition
  `RESERVE_FAIL` (false-entry 0.25, emission precision 0.0). No retune; BEST
  unchanged. Landed via PR #141 then follow-up merge.

- **Wire v3 Stage B retrieval (Spec 007):** invoke family exemplar retrieval
  only on Stage A `EVIDENCE_PRESENT`, calibrate global Stage B floors on the
  evidence-surface validation split, and report reserve-authorization without
  creating a reserve. BEST unchanged.

- **Train v3 Stage A evidence gate (Spec 007):** one authorized train on the
  READY `HYPERLEX_V3_EVIDENCE_SURFACE_V1` against the preregistered
  `false_evidence_entry_rate_on_none <= 0.05` gate. No v3 reserve, BEST
  unchanged.

- **Preregister v3 evidence gate + fresh surface (Spec 007):** freeze
  Stage A labels, false-entry ≤ 0.05, family emission ≥ 0.80, schema hashes,
  and decision semantics; build `HYPERLEX_V3_EVIDENCE_SURFACE_V1` (n=4124,
  train/validation, five subtypes) to `READY`. Spent v2 reserve overlap 0; no
  Stage A train, no v3 reserve, BEST unchanged.

- **Classification v2 final settlement + v3 evidence gate (Spec 007):** seal
  `HYPERLEX_CLASSIFICATION_V2 = RESERVE_FAILED` /
  `APPLICABILITY_GENERALIZATION_FAILURE`; production promotion rejected; BEST
  unchanged. Open `HYPERLEX_CLASSIFICATION_V3_EVIDENCE_GATE` specs/schemas
  (Stage A/B/C, dataset admission, evaluation with preregistered
  `false_evidence_entry_rate_on_none <= 0.05`). No v3 train; spent v2 reserve
  permanently diagnostic only.

- **Family retrieval reserve eval (Spec 007):** `OPERATOR_AUTHORIZE_RESERVE_EVAL`
  scored the sealed classify reserve once under frozen retrieval thresholds
  0.85 / 0.03. Disposition `RESERVE_FAIL` (emission precision 0.409 < 0.80).
  No recalibration, index rebuild, or BEST move.

- **Family retrieval decision (Spec 007):** `HYPERLEX_FAMILY_RETRIEVAL_DECISION_V1`
  makes training-side mean top-M cosine retrieval the canonical Classification v2
  family decision. Residual 18-way head is diagnostic only. Encoder, ontology,
  applicability, corpus, BEST, and reserve isolation stay unchanged. Two global
  validation thresholds calibrate emission precision ≥ 0.80 before any reserve
  score.

- **Forward-hub error decomposition (Spec 007):** read-only
  `HYPERLEX_FORWARD_HUB_ERROR_DECOMPOSITION_V1` audits the sealed forward-hub
  checkpoint (`adf5db93…`) on `civilian.v0.7.hub.jsonl` without training,
  reserve scoring, BEST moves, or prototype mutation. Emits per-family metrics,
  confusion causes, prediction hubs, social-evaluation attractor audit, and a
  single remediation decision.

- **Release-candidate tooling (Spec 007):** `release_set.py` (`HYPERLEX_RELEASE_SET=1`
  drops CC BY-SA rows and same-text rows from train and every eval surface);
  `HYPERLEX_EXPORT_DIR` keeps train runs from rewriting tracked exports;
  `score_holdout.py` (scores once, verifies manifest hashes, copy/majority
  baselines, val-fitted calibration); `launch_train.py` (canonical launcher,
  refuses if busy / no ALLOW_TRAIN / receipt exists); `rc1-train-env.json`
  (morph78 recipe, cold start, strict filler filter, release set).

- **D1 / D5(a) / D8 / A7 (Spec 007):** `license_relabel.py` marks Wiktionary-
  sourced rows `CC BY-SA 4.0`; `filler_filter.py` (`HYPERLEX_FILLER_FILTER`,
  default `strict`) keeps handles, links, and wiki scraps out of the shipped
  filler vocab; amendment A7 (A1 counts trunk parameters); receipts record the
  filter. morph78 recipe pins `HYPERLEX_FILLER_FILTER=off` for reproduction.

- **Publish readiness (Spec 007):** canonical soft_ceiling chain (`soft_ceiling.py`,
  `val_settle.py`, `scripts/spark/soft_ceiling/`) with contamination-safe gate;
  train receipts record code commit / tree hash / env; `HYPERLEX_TASK_ROUTING`
  switch reproduces morph75–78 data prep exactly; order-stable export typology
  (data_sha256 was hash-seed dependent); calibrated lineage (`infer --calibration`);
  Hub remote-code loader. Results: `specs/007-hyperlexical-model/PUBLISH-READINESS-RESULTS-20260924.md`.

- **Publish audit (Spec 007):** recommend keeping `seed-morph78` weights local-only.
  Soft_ceiling broad val shares 193/256 rows with force-train; leak-free val
  (n=63) ties morph78 and morph65 at 1.0. Training ran from an uncommitted Spark
  checkout plus off-git scripts. See `specs/007-hyperlexical-model/PUBLISH-AUDIT-20260924.md`.

- **Trained inference (Spec 007):** `hyperlexical.infer --model-dir` runs a local
  checkpoint (lazy torch, local trunk, fail-closed exit 2) and emits a
  `MODEL_EMBEDDING` inference packet; only the approved pin carries
  `hyperlex-structure-149m`. Default CLI stays the offline stub.

- **Card rename (Spec 007):** Hub card `hyperlex-structure-149m` for `seed-morph78`.
  `name_gate.py` pins the approved checkpoint; `eval_unbind` sets `name_gate`
  true only for a trunk-forward eval of that pin; eval schema field is boolean.
  Training contract and HF dump writer unchanged (new checkpoints stay unnamed).

- **`name_gate` yes (`seed-morph78`):** Danny `flip name_gate` — pin may be called
  **Hyperlexical** (amendment A6; receipt `specs/007-hyperlexical-model/receipts/20260924-name-gate-yes-morph78.md`). Card IDs, packet/schema
  field, Hub, and T13 unchanged.

- **Naming persistence lock:** `docs/NAMING.md` + Notion Naming lock page +
  Public Claims CLAIM-HLX-NAME-001/002/003. Operator Hub / Spine Owner /
  Core Model Spine updated. Org mirror stays lag (do not train from it).
  Does **not** flip Hyperlexical `name_gate`.

- **Operator name ne0l0gist (ingest):** Danny `name neologist as in repo` —
  public ingest product **`ne0l0gist`** (repo spelling). Receipt
  `specs/007-hyperlexical-model/receipts/20260924-name-ne0l0gist-as-in-repo.md`.
  Does **not** flip Hyperlexical `name_gate`.

- **Hygiene + name-gate plan:** `pyproject.toml` version aligned to `VERSION`
  **0.4.0**; ROADMAP trained-E2 line (no stale Spark-blocked checkbox); drop tracked
  `__pycache__`, tip probe, `.tmp` restore junk. Draft
  `specs/007-hyperlexical-model/NAME-GATE-AND-NAMED-PHRASES.md` (morph77 HOLD
  phrases already settled; morph78/reprobe empty; Danny yes still required).
  Does not flip `name_gate`.

- **Spec 007 tip CI: restore unbind force-train API:** `loop.py` imported
  `apply_unbind_force_train` but tip `unbind_recipe.py` lacked the helpers
  (`HYPERLEX_UNBIND_FORCE_TRAIN_PATH`, resolve/load/apply). Restored + tests
  `tests/shadow/test_hyperlexical_unbind_force_train.py`.

- **Spec 007 Hyperlexical product plan (draft):**
  `specs/007-hyperlexical-model/HYPERLEXICAL-PRODUCT-PLAN.md` — climb under
  soft_ceiling, engineering hygiene, name_gate/Hub packaging, PR triage
  (#100 / #99 / #95). Does not flip `name_gate`.

- **Spec 007 morph74 IN FLIGHT (SoT clean + acquire-settle):** quarantined **57**
  INFERRED wiki/scaffolding from Spark SoT; durable `reject_wiki_scaffolding_text`.
  Settle `to the moon` + `elo hell` → force/hard **217→221 / 258→262**. Warm
  morph65 + `INIT_EXPAND_VOCAB=1`. Fair **0.9880239520958084** n=167. Container
  `hlx-train-morph74-1790179734`. Receipts:
  `receipts/20260923-sot-clean-acquire-civilian.md`,
  `receipts/20260923-morph74-acquire-settle-inflight.md`.

- **Spec 007 morph73 REJECT_VS_BEST:** expand-warm tied fair **0.9649122807017544**
  n=171 → REJECT. Residual AUTHORIZE=0 scaffolding — cleaned for morph74.

- **Earlier Unreleased Spec 007 / docs / P1 entries:** morph72→morph56 ladder and
  0.4.0… history preserved in branch history / operator workspace `CHANGELOG.md`.
