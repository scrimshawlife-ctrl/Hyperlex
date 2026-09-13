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

### WF-003 extension: reviewed contract adapter

Purpose: translate declared reviewed supervision into an explicit task selection
without replacing unknown labels with negatives. Actors: engineer, reviewer,
pure adapter. Trigger: validated source/annotation/split bundle is available.
Preconditions: caller declares the expected ontology version; existing operator
and source-review boundaries hold. Inputs: dataset and expected ontology version.
Happy path: validate joins and groups, require reviewed status for every active
head, validate family vocabulary/cardinality, preserve occurrence IDs and offsets,
map dev to val explicitly, and produce rows plus exhaustive accounting.
Alternates: no active supported supervision excludes the example with a reason.
Failures: active typology/stage, weak active labels, ontology mismatch or invalid
family labels reject the batch. No partial results, files, network or training.
States: VALIDATED -> ADAPTING -> REJECTED | ADAPTED_NOT_RUNNABLE. These are terminals.
Invariants: test partitions remain test; raw text and span array order are retained;
no OBSERVED promotion, inferred family, new license or approval declaration.
Permissions: pure local engineering. Audit: dataset/rows hashes, example-level
exclusions, selected task counts and remaining runtime blockers.
Acceptance: ADP-001 complete accounting; ADP-002 explicit reviewed masks;
ADP-003 unchanged occurrence identity; ADP-004 unsupported supervision rejection.
Dependencies: WF-001/002 and routing. Unresolved: reviewer/source truth is external;
the legacy loop still searches first text occurrence and cannot consume these
spans safely. Adapter rows use role_scheme=reviewed_occurrences and must not be
passed to the legacy loop until occurrence-aware alignment is integrated and tested.
Structure labels retain their original metadata; span roles/fillers supply the
prospective targets. This does not certify structure-label ontology semantics.

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
Combined unbind activation additionally requires nonempty aligned role/filler
lists and each distinct filler occurring exactly once, case-sensitively, in text.
Missing semantic targets and ambiguous repeated occurrences suppress only that
unbind assignment; an active classifier remains selected. Count suppression in
combined_unbind_suppressed; if no task remains, record invalid_combined_unbind_targets.
This check addresses PR 62 review 3998854610; it does not prove tokenizer coverage
or semantic annotation truth and does not change legacy unbind-only validation.
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

### WF-003 extension: private preparation and occurrence alignment

- Purpose: compose WF-002 intake and reviewed adaptation into one auditable local
  package, without falsely declaring a runnable trainer or approved dataset.
- Actors: operator, source/annotation reviewer, preparation tool, offline validator.
- Trigger: explicit preparation request; tokenization is optional diagnostic input.
- Preconditions: Python + jsonschema; authorized private input; existing output
  parent; new output directory; explicit expected ontology. No GPU or network.
- Inputs: JSONL (or one explicitly named ZIP member), optional digest-keyed review
  metadata, optional dataset-bound codepoint tokenization sidecar.
- Happy path: validate intake and grouped joins; adapt reviewed supported heads;
  align explicit occurrences; preserve test rows; emit hash-bound files and receipt.
- Alternate paths: absent review metadata produces quarantine, never synthesized
  approval. Missing offsets block structure while retaining reviewed family selection.
- Failure paths: invalid/duplicate JSON, ontology mismatch, stale tokenization hash,
  missing/extra tokenization example, overlapping/out-of-range offsets, boundary
  spillover and truncated non-whitespace coverage fail closed. Existing outputs
  are refused. Partial directories without receipt.json are incomplete.
- State transitions: REQUESTED -> INTAKE -> ADAPTING -> DATA_BLOCKED |
  PREPARED_NOT_RUNNABLE; invalid input/output -> PREPARATION_FAILED.
- Terminal states: DATA_BLOCKED (exit 3), PREPARED_NOT_RUNNABLE (exit 0),
  PREPARATION_FAILED (exit 2). None is training authority.
- Side effects: preview stdout only; explicit export creates fixed private files,
  preserves original bytes and writes the receipt last. ZIP members are not extracted.
- Invariants: all input records reconcile to quarantine + adapted + excluded;
  unknown is not none; test never enters selected train/val IDs; repeated fillers
  retain distinct occurrence IDs and token positions; name_gate/training_ready=false.
- Permissions: authorized local read/new-directory write; OS ACLs are operator-owned.
  No trainer launch, remote upload, checkpoint creation or promotion.
- Observability/audit: input/container/metadata/dataset/rows/tokenization hashes,
  selected IDs by head/partition, exclusions, blocked alignments and reason counts.
  Public stdout contains aggregates, not source text. Private plan contains raw text.
- Acceptance: PREP-001 hash-bound deterministic package and no overwrite;
  PREP-002 every input accounted; PREP-003 repeated/Unicode/multiword occurrences;
  PREP-004 truncation, whitespace offsets and stale sidecar rejection;
  PREP-005 reserved tests and missing-supervision blockers.
- Dependencies: WF-001 contracts, WF-002 review intake, reviewed adapter and merged
  PR #62 legacy combined-target guard, which remains unchanged.
- Unresolved items: actual rights/reviewer evidence, near-duplicate group completeness,
  frozen production split ID, real tokenizer identity/compatibility, trainer loading,
  evaluation and resumable Spark runtime proof. Tokenization declarations are not
  independently reproduced tokenizer evidence. This does not govern or activate.

The new pure `prepare_reviewed` path does not use the legacy text-uniqueness guard
for its occurrence-aware head selection. It records legacy routing separately as
`legacy_routing_diagnostic`. `run_loop` still rejects reviewed_occurrences before
writes or model loading. No reviewed row can reach first-occurrence fallback.
Aligned spans are gold-span diagnostic supervision, not surface-only inference
or proof of recovery from a bound vector. Token offsets must refer to the exact
encoding used later; no whitespace-tokenizer substitute is silently introduced.
Role/filler vocabularies are sorted and built only from selected structure training
rows. Family IDs retain the existing ontology order. Held-out unknown targets keep
their raw values and explicit target_known masks alongside ID zero; matching two
unknown IDs must never count as exact recovery. Literal reserved <unk> targets
are rejected. No validation or test target extends the training vocabulary.

Tokenization sidecar has exactly `dataset_sha256`, `tokenizer_revision`,
`offset_unit="unicode_codepoint"`, and `examples` mapping every active structure
example ID (including held-out IDs) to ordered [start,end] offsets. Only [0,0]
marks ignored special/padding tokens. Non-special offsets must be monotonic and
non-overlapping; partial tokens crossing a gold occurrence are conservatively
rejected. Subword whitespace gaps are allowed, uncovered non-whitespace is not.

Private exports: original.jsonl, optional metadata.json/tokenization.json,
dataset.json, plan.json, quarantine.json, review_queue.json, receipt.json.
Archive input also retains container.zip. Verification checks its byte hash and
the uniquely named member against original.jsonl. Receipt fields must match the
exact recomputed key set; extra claims are rejected. Older archive receipts that
did not retain the container must be regenerated into a new directory, not
silently marked verified by this stricter verifier.
The final receipt hashes all other emitted files. It is not a signature or a
transactional/tamper-proof store. Intake split ID remains staging-only.

```text
python -m scripts.shadow.hyperlexical.training_prepare --input PRIVATE.jsonl --ontology EXPECTED_VERSION --out-dir NEW_PRIVATE_DIRECTORY
python -m scripts.shadow.hyperlexical.training_prepare --input PRIVATE.jsonl --metadata REVIEWED.json --tokenization OFFSETS.json --ontology EXPECTED_VERSION --out-dir ANOTHER_NEW_DIRECTORY
```

PREP-001..005 -> tests/shadow/test_training_prepare.py; ADP-001..004 ->
tests/shadow/test_training_adapter.py. No source reviewer decisions are generated
by this implementation. Preparation infrastructure completion is distinct from
real dataset eligibility and trainer integration.

REC-001 -> WF-003 -> test_contract_rejection, test_clean_no_mutation_or_authority.
REC-002 -> WF-003 -> test_missing_train_signal, test_missing_dev_signal, test_missing_test.
REC-003 -> WF-003 -> test_historical_bytes_and_negative_controls.
REC-004 -> WF-003 -> test_cli, test_clean_no_mutation_or_authority.

Implemented: read-only recovery diagnostic and synthetic controls; occurrence-aware
preparation (#63); explicit reviewed trainer path (`training_reviewed_loop.py`) that
consumes `PREPARED_NOT_RUNNABLE` plans only, preserves occurrence IDs / pinned
`token_indices` / train-only vocabularies, refuses train-set eval fallback, audits
that consumed example IDs ⊆ selected train IDs, records runtime/recipe identity in
consumption receipts, refuses BEST overwrite claims, and checks uninterrupted-vs-
resumed weight equality on synthetic eligible plans. Legacy `run_loop` still rejects
`role_scheme=reviewed_occurrences` before write/model load.

Local CPU synthetic smoke (2026-09-13): resume weights_equal=true; consumption audit
passed; family_exact=1.0 on held-out family head; structure_exact_known_only=null
because val fillers are intentionally unknown under train-only vocabularies.

### Private queue + synthetic pipeline proof (2026-09-13)

- Dump review package remains private (`QUEUE_BUILT`, `training_ready=false`); no dump rows were auto-approved.
- Tooling path proven on synthetic-only rows: review apply → intake → prepare/verify → reviewed trainer resume (`weights_equal=true`).
- Next real gate: human P1 (`observed` + `operator-attested`) decisions with authoritative rights references, then prepare on that subset only.

### P1 provenance gate (2026-09-13)

P1 dump rows (`OBSERVED` + `operator-attested`, n=383) carry Notion provenance
pointing at `Hyperlex-Vernacular-export-2026-09-10` with `operator-blanket-yes`
settle notes. Those notes are **not** authoritative `rights_reference` values.
Notion MCP auth (Cursor desktop) is required to inspect the export page and mint
a real rights memo before any confirm flags may be set. Private workbench:
`/tmp/hlx-p1-workbench-20260913` (family-only starter; zero gold spans).

### Merged reviewed trainer + continued P1 CPU pretrain (2026-09-13)

- PR [#64](https://github.com/scrimshawlife-ctrl/Hyperlex/pull/64) squash-merged to
  `main` (`fcca166`): reviewed trainer + review-queue validate/operator-* bans.
- Private P1-383 prepare package verified locally (`PREPARED_NOT_RUNNABLE`,
  blockers `[]`); dump/memo packages stay outside git.
- Family-only CPU reviewed pretrain resumed from step 200 → 2000 on that package
  (`best_overwrite=false`, `training_ready`/`name_gate` still false). Val
  `family_exact` plateaued ~0.66 on the toy hash-embedding trainer; structure
  supervision still blocked (zero gold spans). Spark Option A not available on
  this host (`SPARK_HOME` unset). Do not overwrite BEST (morph19).

### Post-merge continue slice (2026-09-13)

- Held-out eval on continued h64 ckpt: val `family_exact`≈0.66 (n=38), test≈0.76
  (n=25); structure metrics null; gold-span diagnostic n_rows=0.
- Fresh capacity bump (hidden=128, 2000 steps, not resumed) matched the same
  plateau (val≈0.66 / test=0.76) — not a hidden-size bottleneck on this toy
  trainer + family-only package.
- Dump probe: all 5019 roles/fillers empty; P1 metadata structure stays
  `unreviewed` with empty spans — nothing to auto-promote to structure head.
- Private packages (outside git): P1 structure annotation worksheet
  `/tmp/hlx-p1-structure-worksheet-20260913` (383 rows, confirm_*=false);
  P3 triage workbench `/tmp/hlx-p3-workbench-20260913` (190 rows, policy block
  against auto-approving `operator-local`). Notion MCP still `needsAuth` here.


### Spark Option A smoke on verified P1 (2026-09-13)

- Reachability: `ssh spark` (Cloudflare tunnel → `morpheus@spark-bf46`) works; this
  cloud VM has no local Apache/`SPARK_HOME` — Spark means the DGX host.
- Isolated worktree `~/Hyperlex-reviewed-smoke` at `main` (`005d45d`); morph19
  checkout left alone.
- Verified private P1-383 `prepare_clean` copied to
  `~/hlx-private/p1-confirmed-20260913-full/prepare_clean` (outside git).
- Bounded reviewed-trainer smoke via Spark docker torch stack
  (`lmsysorg/sglang:…`, torch 2.13+cu130). First GPU attempt OOM'd against resident
  Qwen VRAM; reran with `CUDA_VISIBLE_DEVICES=` empty so the toy trainer does not
  init CUDA. Resume `weights_equal=true`; val `family_exact`≈0.66; structure null.
- BEST/morph19 untouched: path + `model.safetensors` mtime unchanged;
  `best_overwrite=false`; `training_ready`/`name_gate` still false.
- Receipt: `~/hlx-private/p1-spark-smoke-20260913/SMOKE_SUMMARY.json` (private).

Remaining ordered execution tasks:
1. Human structure gold spans on P1 worksheet (or subset) → re-prepare → structure
   head train. Do not invent spans.
2. Expand rights/review beyond P1 only with explicit operator policy; do not
   auto-approve `operator-local` bulk (P3 workbench is triage-only). Dump SHA-256
   `b6867a4f441197b78dbfea71a8936894c62f8fa3b4343dc093043e6069e67d7e` (5019 lines).
3. Optional: GPU morph/trunk smoke with explicit VRAM budget (Qwen resident) —
   still never BEST overwrite without explicit approval. Reviewed-path Spark smoke done.

Provenance: Notion Sprint 001 Hub NOT_COMPUTABLE + Loop 805 Slice N/A + Hash:
e1414f86e7a0d5494404af27d9c616302268b182 (post-#64 recovery tip before this note).
