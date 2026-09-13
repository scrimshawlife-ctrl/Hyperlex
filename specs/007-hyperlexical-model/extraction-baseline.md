# Spec 007: structural baseline and data review

## Doctrine and boundary

Reference existing Spec 007 locks. SHADOW only; this does not govern or activate.
No training, pinning, publication, label promotion, or benchmark replacement.
This is a structural comparator, not a new learned model.

## Domain model

A Surface is raw text. An Occurrence has a zero-based index, start/end Unicode
character offsets, exact filler text, and a structural role. An EvaluationRow
adds gold fillers/roles only for scoring. A ResidualRow also includes prior
predictions and stored counters. A ReviewCandidate is not approved gold.

## Requirements

- EX-001: predict using only text and declared role scheme, never gold labels.
- EX-002: preserve case, punctuation, and distinct repeated occurrences.
- EX-003: malformed inputs are counted and yield a nonzero CLI exit.
- EX-004: label residual-only results and never equate them with full validation.
- EX-005: inputs, training data, and promotion gates remain unchanged.

## Journeys

Operator compares model residuals to a simple structural baseline. Reviewer
then distinguishes task construction, source hygiene, and genuine extraction
requirements before proposing independent train-only annotations.

## Workflows

IDs below are scoped to Spec 007; no existing WF-### references were found in
the inspected Markdown/JSON inventory. They create no new operational authority.

### WF-001 — Offline baseline evaluation

- Purpose: determine whether the declared surface grammar already recovers targets.
- Actors: operator, local CLI, reviewer.
- Trigger: operator supplies input JSONL and explicit population.
- Preconditions: authorized local input; no model or network required.
- Inputs: text, role_scheme; gold/roles and optional prior counters for scoring only.
- Happy path: read bytes, hash, parse, predict spans from text, validate targets,
  score, emit aggregate report to stdout.
- Alternate/failure paths: malformed JSON/empty file exits 2; malformed rows
  are counted as rejected and remain in the denominator; any rejection exits 2.
- State transitions: received -> parsed -> evaluated -> reported; file failure
  -> aborted; row rejection -> reported_with_rejections.
- Terminal states: reported, reported_with_rejections, aborted.
- Side effects: stdout only; input files are never written by the CLI.
- Invariants: no gold-dependent predictions; exact surface fidelity; no name gate.
- Permissions: local read only; operator controls any shell output redirection.
- Observability/audit: input SHA-256, population, accepted/rejected counts,
  rejection reasons, exact denominators, duplicate count, scheme/length counts.
- Acceptance criteria: EX-001 through EX-005; synthetic positive and negative
  controls pass; changing gold alone changes score, not prediction.
- Dependencies: Python standard library; positional/type-slot grammar below.
- Unresolved items: semantic role discovery and actual model comparison require
  full validation predictions and a verified checkpoint manifest.

### WF-002 — Data review and independent annotation handoff

- Purpose: improve task examples without contaminating evaluation or inventing gold.
- Actors: operator, annotator, reviewer; no automatic adjudication.
- Trigger: WF-001 or a model residual report identifies a review candidate.
- Preconditions: preserve current benchmark and provenance; reviewer available.
- Inputs: authorized raw source, context, residual reason, phrase/source group ID.
- Happy path: classify source kind; separate term/context/definition/citation;
  mark exact spans and occurrences; review rights and labels; select independent
  train-only examples under existing group-split policy; hand off reviewed queue.
- Alternate/failure paths: uncertain source rights, ambiguous roles, missing
  source, or evaluation overlap -> quarantine; disagreement -> adjudication.
- State transitions: candidate -> reviewed -> eligible_for_handoff;
  candidate/reviewed -> quarantined; disagreement -> needs_adjudication.
- Terminal states: eligible_for_handoff, quarantined, needs_adjudication.
- Side effects: proposed private annotation records only after explicit approval;
  this patch does not create a corpus, write Notion, or modify labels.
- Invariants: validation residuals stay out of training; synthetic examples
  never become OBSERVED usage evidence; unknown family is not a negative label.
- Permissions: reviewer approves annotation; existing operator gates control
  training and publication independently.
- Observability/audit: original label, proposed label, source ID/hash, reviewer,
  reason, rights status, group ID, split version, and annotation status.
- Acceptance criteria: no evaluation-group overlap; every approved target has
  source-backed spans and review provenance; unresolved rows remain excluded.
- Dependencies: source access, annotation guide, group split inventory.
- Unresolved items: live SoT/Notion reconciliation and reviewer decisions remain
  NOT_COMPUTABLE; workflow is documented, not automatically executed.

## State machines, contracts, and data model

WF-001 states are described above. CLI requires `--input` and `--population`
(`residual_only` or `evaluation_set`). Evaluation sets must contain only
`task=unbind` rows, with `fillers`, `roles`, `text`, and `role_scheme`.
Residual inputs require `gold`, `pred`, `roles`, `text`, `role_scheme`, and all
six stored counters emitted by the existing residual writer. Counters must
agree exactly; boolean values are not integers for this contract.

Positional grammar: each maximal non-whitespace span is a filler, role pos_i.
Type-slot grammar: every maximal non-whitespace token is ROLE:atom, where ROLE
is TOKEN, SLOT, or MARKER and atom is nonempty. Split only at the first colon.
Embedded whitespace in an atom is outside this grammar; no fallback is allowed.
Type roles are already encoded in the input; parsing them is not semantic inference.

Review record fields: source_kind (term/context/definition/citation/markup),
raw_text, canonical_term, context, source_id, source_hash, rights_status,
original_labels, proposed_labels, occurrence_spans, review_status, reviewer,
reason, group_id, split_version. These are proposed review fields, not changes
to existing dataset schemas or an invented SoT.

## Security, privacy, and governance

CLI does not load weights, call the network, log raw rows, change inputs, or
change gates. Generic file errors avoid exposing private paths/content.
Reports contain aggregate information; review before sharing. No URL in input
is followed. No provenance upgrade is inferred from structural correctness.

## Architecture

`extraction_baseline.py` is an independent standard-library comparator.
`extract(text, role_scheme)` has no access to gold. `evaluate` validates and
scores after prediction. Existing training, alignment, inference, exports,
evaluation metrics, and pin rules are deliberately untouched.

## Acceptance, traceability, tasks, verification

| Requirement | Workflow | Test |
|---|---|---|
| EX-001 | WF-001 | test_gold_is_not_prediction_input |
| EX-002 | WF-001 | test_offsets_preserve_occurrences |
| EX-003 | WF-001 | test_bad_grammar_rejected, test_rejected_rows_stay_in_denominator |
| EX-004 | WF-001 | test_residual_counter_control |
| EX-005 | WF-001/002 | test_cli_read_only_and_private_diagnostics; patch boundary review |

Implemented: structural baseline, aggregate audit, CLI, negative controls.
Documented only: annotation handoff WF-002. Training/model architecture changes
are a separate experiment after baseline reconciliation, not completed here.

From the repository root, with an environment containing Python:

```sh
python -m scripts.shadow.hyperlexical.extraction_baseline --input /path/to/residual.jsonl --population residual_only
python -m pytest tests/shadow/test_hyperlexical_extraction_baseline.py -q
```

A perfect structural score is not model improvement, E2 proof, semantic
understanding, or authorization to pin. Never substitute it for unbind_exact.

Provenance: Notion Sprint 001 Hub NOT_COMPUTABLE + Loop 805 Slice N/A + Hash: b3eee725054c1ed1dae16fad3464af005edad0cc (base)
