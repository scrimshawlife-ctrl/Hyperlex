# Opt-in training intake converter

## BOUNDARY / EVIDENCE PACKET
Proposed SHADOW execution helper. No current dataset migration, label promotion,
run fabrication, training, or Notion writeback. This does not govern or activate.
The source files and review sidecar remain authoritative; conversion only checks
their declarations and prepares review candidates.

## Domain / requirements / journey
An input is UTF-8 JSONL. Each nonblank line is one legacy record, identified by
its canonical JSON digest. A reviewer-supplied metadata object maps that digest
to exactly `source`, `annotation`, and `partition`. These are the proposed v1
source/annotation definitions and train/dev/test partition respectively.
No metadata is inferred from class=OBSERVED, a license string, or a filename.
Original input and sidecar bytes are retained unchanged on explicit export.

- IN-001: every nonblank record is a candidate or quarantine item.
- IN-002: missing evidence never becomes an invented declaration.
- IN-003: original bytes are preserved; existing output directories are refused.
- IN-004: candidates pass dataset contracts together, without fabricated run data.
- IN-005: residual-format rows (gold and pred fields) may only be assigned dev.

Journey: operator previews legacy data -> reviewer supplies real metadata ->
operator converts to a new private directory -> review precedes any integration.

## WF-002 extension — Quarantine-first conversion
Purpose: prepare reviewed records without inventing evidence.
Actors: operator, annotator/reviewer, local converter.
Trigger: CLI invocation with input and optional metadata/output directory.
Preconditions: authorized local input; Python plus jsonschema; output parent
already exists; explicit export directory does not exist.
Inputs: JSONL and optional digest-keyed sidecar; source.raw_text must equal the
legacy text exactly. Missing source context cannot be attached speculatively.
Happy path: parse original -> match exact record digest -> validate metadata
and per-record dataset -> validate candidate batch -> emit preview or new export.
Failure paths: invalid rows/missing metadata -> quarantine; residual assigned
outside dev -> quarantine; cross-record conflicts -> quarantine all otherwise
eligible candidates in that batch. Unused sidecar entries are reported. Invalid
whole sidecar/encoding/empty input or output failure -> INTAKE_FAILED, exit 2.
States: received -> matched -> validated -> candidate; received/matched/validated
-> quarantined; export_requested -> exported or incomplete_export.
Terminal states: previewed, exported, quarantined, failed/incomplete_export.
Side effects: none in preview. Export creates only a new directory's fixed
files; it never overwrites or deletes input/output. A partial export is retained
for diagnosis, has no final receipt, and must not be consumed.
Invariants: no run/checkpoint creation; training_ready=false; name_gate=false;
all source/annotation declarations come from sidecar; residuals stay out of train.
Permissions: local authorized read; explicit new-directory write only. Use
private storage with suitable OS permissions; the tool does not set file ACLs.
Audit: whole input/sidecar byte hashes; original line numbers; per-line and
canonical record digests; reason counts; unused sidecar count; final receipt.
Acceptance: IN-001..005 tested with positive metadata and negative controls.
Dependencies: proposed dataset validator, existing provenance/rights policy.
Unresolved: human truth of sidecar, ontology validation, temporal/near-duplicate
group discovery, and training integration remain outside this helper.

## Contract and architecture
Sidecar root is an object, keyed by lowercase 64-character canonical row digest.
`training_contracts.digest(row)` defines canonicalization. No duplicate JSON
properties or non-finite numbers are accepted. Whitespace-only lines are not
records but remain preserved in original bytes. Per-line hashes cover decoded
line content re-encoded as UTF-8 without the line ending; the whole-file hash
covers exact bytes, including BOM and line endings.

Source and annotation are supplied rather than manufactured. Dataset validation
is now separately callable as `validate_dataset` without any run/evaluation
records. Existing full-bundle validation invokes it and keeps its prior checks.
The intake split ID `intake-review-v1` identifies staging only, NOT a frozen
training split. Preserve actual freeze IDs when later assembling a reviewed run.

Export files: `original.jsonl`, optional `metadata.json`, `candidates.json`,
`quarantine.json`, `dataset.json`, `receipt.json`. Dataset is null when no
candidate remains. Quarantine records reference original line/hash and reason;
they do not repeat raw text. Candidate records may contain private source text.
Receipt is written last; `export_complete=true` indicates write completion, not
training readiness. Export files are not a transactional, tamper-proof store.

Exit 0 means no quarantine/unused metadata; exit 2 means review/error remains.
A completed quarantine export therefore legitimately exits 2.

## Usage / validation / traceability
From repository root:

```sh
python -m scripts.shadow.hyperlexical.training_intake --input /private/legacy.jsonl
python -m scripts.shadow.hyperlexical.training_intake --input /private/legacy.jsonl --metadata /private/reviewed-sidecar.json --out-dir /private/new-intake
python -m pytest tests/shadow/test_training_intake.py -q
```

IN-001: malformed-row/duplicate-row tests. IN-002: missing metadata, rights,
reviewer, text and span controls. IN-003: byte-preservation/no-overwrite/default
preview tests. IN-004: cross-group conflict and dataset validation controls.
IN-005: residual partition control. No private residuals are committed as fixtures.

## RESIDUAL RISKS / NEXT ADVISORY ACTION
Supplying a sidecar does not establish source rights or annotation truth by
itself. This is intentionally not automatic corpus cleanup. Review the quarantine
queue with actual source records before assembling a complete evidence bundle;
do not populate missing values merely to pass validation.

Provenance: Notion Sprint 001 Hub NOT_COMPUTABLE + Loop 805 Slice N/A + Hash: b3eee725054c1ed1dae16fad3464af005edad0cc (base)
