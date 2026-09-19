# Hyperlex EIC Qualification — HYPERLEX-Q1

Status: `CANON-SHADOW`  
Version: `0.1.0`  
Upstream reference: Noesis `specs/EPISTEMIC-INTERCHANGE.md`

## Purpose

Qualify the canonical Hyperlex work/train repository as a deterministic transformation producer for controlled epistemic-interchange testing.

Passing HYPERLEX-Q1 means Hyperlex can describe what it transformed, what it intended to preserve/change, and how the output was produced without claiming that the declared invariant actually survived in a model representation.

It does **not** validate Hyperlexical, EXP-001, latent semantics, or ecosystem readiness.

## Repository authority

`scrimshawlife-ctrl/Hyperlex` is the canonical train/work remote. `Zero-State-LLC/Hyperlex` is a company mirror and may lag. Qualification evidence MUST bind the canonical work remote revision.

## Doctrine

1. Hyperlex owns transformation generation and transformation provenance.
2. Hyperlex may declare `semantic_intent`, `expected_invariants`, and `expected_changed_attributes` as experiment inputs.
3. These declarations are hypotheses, not observations of latent truth.
4. Hyperlex MUST NOT emit `CALIBRATED` or `SETTLED` merely because a transform completed.
5. A deterministic transform MUST bind source hash, output hash, transform identity/revision, parameters, and runtime/model identity when applicable.
6. Contamination, fallback, nondeterminism, missing model binding, or unresolved provenance MUST be explicit.
7. Missing required evidence yields `NOT_COMPUTABLE` or a typed rejection.
8. Existing Hyperlex provenance semantics remain valid: `OBSERVED`, `INFERRED`, `SPECULATIVE`, `NOT_COMPUTABLE`.
9. Brier/calibration behavior remains governed by existing settlement rules; HYPERLEX-Q1 does not create Brier evidence.

## Journey

### J-HQ1-001 — Export a controlled transform

An experiment runner provides a source fixture and registered transform request. Hyperlex produces an output plus sufficient provenance for Noesis to test the declared invariant independently.

## Workflow

### WF-HQ1-001 — Produce EIC transform fixture

**Actors:** experiment runner, Hyperlex transform adapter.  
**Trigger:** registered controlled-transform request.  
**Preconditions:** source bytes/text hashable; transform identity known; required runtime/model binding known or explicitly unavailable.  
**Inputs:** source, transform class, parameters, declared semantic intent, expected invariants, expected changed attributes.

**Happy path:**
1. Hash source.
2. Resolve transform implementation and revision.
3. Freeze parameters/seed where applicable.
4. Execute transform.
5. Hash output.
6. Record model/runtime revision where applicable.
7. Record declared invariants and changed attributes as declarations.
8. Record contamination/fallback/nondeterminism metadata.
9. Emit transport fixture.

**Failure paths:**
- missing source identity -> reject;
- missing required transform revision -> `NOT_COMPUTABLE`;
- nondeterministic path without declared seed/envelope -> `NOT_COMPUTABLE`;
- fallback route -> explicit fallback provenance;
- contamination detected -> emit contaminated result, never silently clean it;
- transform provider attempts to assert latent truth -> reject contract.

**Terminal states:** `PRODUCED`, `NOT_COMPUTABLE`, `REJECTED`.

**Invariant:** successful generation does not prove semantic preservation.

## Qualification fixture classes

HYPERLEX-Q1 MUST test:

1. deterministic identity transform;
2. deterministic surface rewrite with declared invariant;
3. changed-meaning negative control;
4. false invariance declaration;
5. missing model/runtime binding when binding is required;
6. contaminated source/output;
7. stale transform revision;
8. repeated execution with same registered inputs;
9. fallback execution;
10. malformed or absent provenance.

## Acceptance — AC-HQ1

PASS requires all:

- source/output hashes are stable for deterministic fixtures;
- transform identity/revision and parameters are explicit;
- same deterministic request reproduces the registered output hash;
- declared invariants remain declarations, not observations;
- false-invariance fixture is exportable as a hypothesis but cannot become latent truth;
- contamination and fallback remain visible;
- missing required binding fails closed;
- no HYPERLEX-Q1 output silently gains `CALIBRATED` or `SETTLED`;
- evidence receipt binds canonical repository commit and fixture hashes;
- automated tests pass;
- independent review is recorded or qualification remains provisional.

## Tasks

### T-HQ1-001 — Define transform export schema
Add a versioned Q1 transport schema compatible with the Noesis EIC boundary.

### T-HQ1-002 — Build deterministic fixtures
Implement the ten qualification fixture classes.

### T-HQ1-003 — Build validator
Reject latent-truth promotion, missing required provenance, and undeclared nondeterminism.

### T-HQ1-004 — Qualification receipt
Bind commit, CI runs, fixture hashes, failures, limitations, reviewer, and UTC decision.

## Verification

- V-HQ1-001 schema validation;
- V-HQ1-002 repeat-output hash stability;
- V-HQ1-003 false-invariance declaration remains hypothesis-only;
- V-HQ1-004 contamination survives serialization;
- V-HQ1-005 fallback survives serialization;
- V-HQ1-006 missing binding fails closed;
- V-HQ1-007 stale revision rejected;
- V-HQ1-008 no epistemic promotion;
- V-HQ1-009 canonical remote/revision bound in receipt.

## Downstream gate

`Hyperlex -> Noesis` pairwise conformance remains BLOCKED until both:
- NOESIS-Q1 has qualifying evidence; and
- HYPERLEX-Q1 has qualifying evidence.

Even after both pass, pairwise conformance tests the boundary only. It does not authorize ecosystem-wide EXP-001.
