# Proposed v1 training evidence contracts

## Boundary and doctrine

Reference existing Spec 007 only. SHADOW advisory, no activation or promotion.
These opt-in contracts do not replace the current SoT/export schemas, label
ontology, benchmark, trainer, or pin rules. This does not govern or activate.

## Domain and requirements

`contracts/training/v1.schema.json` is a Draft 2020-12 schema with five versioned
definitions (source, annotation, split, run, evaluation) and a bundle root.
Use the bundled definitions directly; no external reference resolver or network
fetch is needed. Sources may include quarantined material, but annotations in
this validation bundle may refer only to sources declared rights-approved.

- TC-001: trace annotations to exact source text and occurrence offsets.
- TC-002: keep label status per head; unknown/disputed labels cannot enable loss.
- TC-003: assign every example exactly once; declared groups, source IDs and
  normalized exact-text groups cannot cross partitions.
- TC-004: tie runs to the supplied sources, annotations and split content hashes.
- TC-005: distinguish surface extraction, oracle-span diagnostics and bound recovery.
- TC-006: validation reads local input only and cannot train, promote, or publish.

## Journey and workflow integration

Operator validates a proposed evidence bundle before considering trainer
integration. Reviewer distinguishes structural validity from truth of labels,
rights, checkpoint provenance, and runtime behavior.

### WF-001 extension — Contract validation before baseline evaluation

Purpose: detect inconsistent proposed evaluation evidence. Actors: operator,
validator, reviewer. Trigger: explicit local `--bundle` invocation.
Preconditions: Python with jsonschema installed; authorized local JSON bundle.
Inputs: sources, annotations, split, run, evaluation.
Happy path: parse without duplicate properties -> validate schema -> check
hashes/spans/joins/masks/groups -> reconcile evaluation -> emit aggregate receipt.
Alternate/failure paths: invalid JSON, schema or semantic failure -> generic
CONTRACT_INVALID and exit 2; missing dependency is an environment setup failure,
not valid data. State transitions: received -> parsed -> checked -> reported,
or received/parsed/checked -> rejected. Terminal states: reported/rejected.
Side effects: stdout only; caller may explicitly redirect it. Invariants:
name_gate=false, brier=null, no input mutation, no network or model loading.
Permissions: local read only. Observability/audit: bundle hash, source/example
counts, validity result; no raw source text or private paths in diagnostics.
Acceptance: TC-001 through TC-006 tests; run hash/offset/mask/leakage negative
controls fail. Dependencies: shared local schema and jsonschema.
Unresolved: an approved source declaration does not independently verify rights;
declared decoder access is not runtime isolation proof.

### WF-002 extension — Review annotations before handoff

Purpose: preserve per-head provenance and keep evaluation groups out of training.
Actors: annotator, reviewer, operator. Trigger: annotation proposed for handoff.
Preconditions: original source available and existing rights/label policy retained.
Inputs: exact text, source references, occurrence spans, group IDs, per-head labels.
Happy path: review source type/rights -> review each head separately -> assign
existing group partition -> build proposed bundle -> run WF-001 validation.
Failure paths: missing evidence -> quarantine; disputed labels -> loss masked;
overlap -> reject split and request correction rather than silently reassign.
States: candidate -> reviewed -> validated_for_handoff; any stage -> quarantined
or needs_adjudication. Terminal states: validated_for_handoff/quarantined/
needs_adjudication. Side effects: none automatically; private annotations require
normal review authorization. Invariants: no invented OBSERVED evidence, no
evaluation-to-training copying, no automatic taxonomy change. Permissions:
reviewer adjudicates; operator retains training/merge/publication gates.
Audit: method, reviewer, status and loss mask independently per head, source
references and content hashes. Acceptance: active labels have values, reviewed
labels name a reviewer, active structure has spans, groups stay in one partition.
Dependencies: human rights/label review and existing group registry.
Unresolved: semantic validity of family/typology/stage values and near-duplicate
group discovery are not enforced by this first structural-contract slice.

## State machines, contracts and data model

Source v1: raw text, SHA-256 of exact UTF-8 text (no normalization), source kind,
rights status and reference, provenance reference. Original files remain external.
Annotation v1: example/source IDs, one or more group IDs, Unicode-codepoint
offsets, occurrence IDs, ontology version, per-head labels. Ranges are half-open.
Multiple occurrences may have equal text but need distinct offsets/IDs. Identical
coordinates are rejected; overlapping spans are permitted for future nested tasks.
Split v1: stable split ID and exhaustive train/dev/test assignments.
Run v1: code commit and patch hash, input hashes, checkpoint hash, trunk/tokenizer
revision identifiers, seed, environment strings and a minimal recipe. Recipe v1
records sampler, optimizer, learning rate, batch size and epochs; it is NOT a
complete resume checkpoint or guarantee every trainer setting was captured.
Evaluation v1: run/protocol IDs, population, explicit evaluated example IDs,
task, declared decoder access, exact counts and score. Dev/test reports must
cover their entire declared partition; residual-only review is a dev subset.

Hash convention: sources/annotations/split hashes use compact ASCII-escaped JSON
with sorted object keys, original array order, finite numbers and no trailing
newline. Source-text hash instead covers raw UTF-8 text bytes. All arrays retain
order. Exact score must match integer counts within absolute tolerance 1e-12.
Input JSON duplicate keys and non-finite numbers are rejected.

## Security/privacy/governance and architecture

The optional validator imports jsonschema, reads only the local schema and
provided bundle, and prints an aggregate result. No remote schema resolution.
Install the repository's existing schema extra in a suitable local environment;
CI requires no model weights or Spark. No approval authority is created by
CONTRACT_VALID. It means the declarations are internally consistent, not that
rights, labels, checkpoint bytes, exact software revisions or decoder isolation
have been externally verified. No live data migration is performed.

## Acceptance / traceability / tasks / verification

TC-001: span/hash/source-link negative tests. TC-002: loss-mask and reviewer
controls. TC-003: duplicate IDs, coverage and source/declared/normalized-text
overlap controls. TC-004: each run content hash mutation rejected.
TC-005: access mismatch, counts, run and population coverage controls.
TC-006: CLI input unchanged, aggregate-only failure, no activation fields enabled.

```sh
python -m scripts.shadow.hyperlexical.training_contracts --bundle /path/to/proposed-bundle.json
python -m pytest tests/shadow/test_training_contracts.py -q
```

Implemented: schema definitions, bundle validator, synthetic tests.
Not implemented: real dataset conversion, ontology adjudication, temporal splits,
complete optimizer/scheduler resume artifacts, checkpoint-byte verification,
runtime isolation, or a learned bound-vector model. Those remain explicit next
tasks, not implications of a valid contract. The supplied residual file alone
cannot be promoted to this bundle: it lacks source/rights/run metadata.

Provenance: Notion Sprint 001 Hub NOT_COMPUTABLE + Loop 805 Slice N/A + Hash: b3eee725054c1ed1dae16fad3464af005edad0cc (base)
