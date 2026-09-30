# Changelog

## Unreleased

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
