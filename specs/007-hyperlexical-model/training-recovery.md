# Training recovery: advisory local evidence slice

## BOUNDARY

This does not govern or activate. Existing doctrine, ontology, name gate and
operator authority remain unchanged. No Notion writeback, training or promotion.
Historical Notion guidance conflicts with later experiment records; reconciliation
is proposed, not silently applied. This module is not wired into the legacy trainer.

## Domain, requirements and journey

A dataset is sources + per-head annotations + grouped split assignments. A
historical bundle additionally declares a run and evaluation. Matching checkpoint
bytes establish artifact identity, not proof of code execution or optimizer state.

- REC-001: validate candidate dataset contracts without inventing a historical run.
- REC-002: account for active supervision by partition and head.
- REC-003: historical mode requires matching checkpoint bytes and dataset content.
- REC-004: never turn diagnostic success into training authorization.

Operator journey: locate available evidence, inspect read-only results, repair
the dataset or explicitly choose a new baseline, then request runtime smoke checks.

## WF-003 — Recover evidence or establish a clean baseline

- Purpose: identify reproducible starting evidence without fabricating history.
- Actors: operator, local engineer, offline validator; Spark operator for later smoke.
- Trigger: training restart requested after missing historical receipts.
- Preconditions: local read permission; no automatic training; reviewed scope.
- Inputs: dataset contract, optional historical bundle and checkpoint file.
- Happy path: validate dataset; count supervision; check checkpoint hash and
  historical dataset equality when supplied; emit a diagnostic JSON to stdout.
- Alternate path: omit both historical inputs to propose a clean baseline. This
  makes no morph19 reproduction claim. Human evidence review is still required.
- Failure paths: bad contracts, duplicate JSON keys, missing/unreadable files,
  hash mismatch or changed historical dataset fail with exit 2. Missing train
  supervision, per-trained-head development supervision or reserved test records
  returns DATA_BLOCKED with exit 3. No silent fallback on invalid historical input.
- State transitions: REQUESTED -> VALIDATING -> INVALID_EVIDENCE | DATA_BLOCKED |
  DATA_CONTRACT_CHECKS_PASSED. The last state is not TRAINING_READY.
- Terminal states: those three diagnostic outcomes; operator chooses next action.
- Side effects: stdout only; no dataset/checkpoint writes, network or subprocess.
- Invariants: training_ready=false, name_gate=false; no historical metric changes.
- Permissions: read named local files; no execution, publication or Notion authority.
- Observability/audit: aggregate supervision, dataset and checkpoint hashes,
  explicit blockers and remaining checks. Raw text and filesystem paths not emitted.
- Acceptance: REC-001..004 synthetic positive and rejection controls pass.
- Dependencies: WF-001 contract validation; WF-002 source/annotation review.
- Unresolved items: actual rights/reviewer proof, exact Spark consumption,
  optimizer/RNG recovery, runtime compatibility and Notion reconciliation.

## Contracts, data and architecture

### WF-003 extension: legacy loop task routing

REC-005: account for every exported row once as selected, masked, or reserved
test; a combined row may contribute to both supported task selections.
REC-006: apply explicit family/structure masks before recipe shaping and model load.

Purpose: prevent combined-task omission and make supervision selection auditable.
Actors: local engineer and existing loop. Trigger: run_loop receives export rows.
Preconditions: existing training gate remains external; routing grants no permission.
Inputs: legacy rows with task classify, unbind or classify+unbind; split train,
val or test; optional loss_masks containing exactly two booleans, family/structure.
Happy path: validate declarations, preserve order, route selected tasks, then
shape only selected unbind training rows. Emit task_accounting in the run receipt.
Alternates: missing masks retain legacy task declarations, counted separately;
false masks disable supervision, never synthesize a negative family label.
Failures: unsupported tasks/splits, malformed masks or active undeclared tasks
raise before export writes or model load. No partial selection returned.
States: EXPORTED_IN_MEMORY -> ROUTING -> REJECTED | SELECTED_FOR_RECIPE.
Terminal states: rejected or returned selection; neither establishes training readiness.
Side effects: router has none; existing loop side effects remain separately gated.
Invariants: test rows never routed; masks cannot add tasks; input rows unchanged.
Permissions: local engineering change only; no production, promotion or Notion write.
Audit: input digest, explicit versus legacy mask counts, exclusive row outcomes,
task/partition counts. Counts are before recipes, not consumed optimizer examples.
Acceptance: REC-005/006 -> test_combined_accounted_once_assigned_twice,
test_independent_masks, test_recipe_receives_only_selected_unbind and run-boundary tests.
Dependencies: legacy exporter and recipe; WF-002 review remains outstanding.
Unresolved: exporter does not yet carry reviewed contract labels into these masks;
legacy rows still lack review proof. Typology/stage are not supported loop heads.
The structure mask disables both role and filler losses as one task; independent
role/filler masks would need a separate contract. Existing oracle-span evaluation,
validation vocabulary use and training-set evaluation fallback remain unfixed.

This implementation changes selected populations for combined-task exports.
New results must not be presented as exact historical recipe reproduction.

Reuse contracts/training/v1.schema.json. Do not introduce another authority
schema. training_recovery.py calls validate_dataset and, in historical mode,
validate; checkpoint bytes are streamed through SHA-256, never deserialized.
The JSON report counts weak and reviewed active labels alike; it does not certify
their truth. Declared variant grouping can be incomplete. Reserved test existence
does not prove untouchedness, adequate size, coverage or reliable evaluation.

Run locally from repository root:

```text
python -m scripts.shadow.hyperlexical.training_recovery --dataset PRIVATE_DATASET.json
```

Historical mode adds --historical-bundle PRIVATE_BUNDLE.json --checkpoint CHECKPOINT.
Exit 0 means only these data/byte checks passed. Never use it as a train launch gate.

## Acceptance, traceability, tasks and verification

REC-001 -> WF-003 -> test_contract_rejection, test_clean_no_mutation_or_authority.
REC-002 -> WF-003 -> test_missing_train_signal, test_missing_dev_signal, test_missing_test.
REC-003 -> WF-003 -> test_historical_bytes_and_negative_controls.
REC-004 -> WF-003 -> test_cli, test_clean_no_mutation_or_authority.

Implemented: read-only recovery diagnostic and synthetic controls.
Remaining ordered execution tasks (not completed by this slice):
1. Review real source use and annotations through WF-002; freeze grouped splits.
2. Integrate contracts into exporter/loader; account for combined tasks and masks.
3. Correct repeated occurrence alignment and seed ordering/sampling.
4. Record exact code, environment, inputs, recipe and resumable checkpoint state.
5. Verify tiny overfit, uninterrupted/resumed equivalence and task-safe evaluation
   on Spark under an approved compute budget; then run the bounded baseline.

Provenance: Notion Sprint 001 Hub NOT_COMPUTABLE + Loop 805 Slice N/A + Hash: b3eee725054c1ed1dae16fad3464af005edad0cc (base).
