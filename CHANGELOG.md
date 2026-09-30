# Changelog

## Unreleased

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
