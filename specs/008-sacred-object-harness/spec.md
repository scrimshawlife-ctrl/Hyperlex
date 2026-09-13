# Spec 008 — Sacred-Object Monitorability Harness (SHADOW)

**Feature**: Eval harness for slang-as-sacred-object in A2A + RAG delivery
**Date**: 2026-09-10
**Status**: SPECIFY draft / SHADOW / not implement
**Depends on**: constitution v1.0.0 I–X; specs 000, 001, 003, 007
**Does not open**: 006 IsA
**Does not amend**: 007 losses, E2, T2 LoRA, dual-use rows
**Lane**: SHADOW / advisory
**Home (v0.1)**: `scripts/shadow/sacred_object/` — never `src/hyperlex/` until a later T-promote sentence
**Packet**: `hyperlex.sacred_object.eval.v0.1`
**Companion**: `dual-use-gate.md`, `owasp-mapping.md`, `plan.md`, `tasks.md`, `room-b-protocol.md`, `finding-template.md`, `schemas/sacred_object_eval.v0.1.schema.json`

## Intent

007 is a structure encoder. 008 is the testbed that asks what *other* agents and RAG stacks do when a civilian attested atom is treated as load-bearing context.

Sacred here is operational, not theological. A sacred object is a high-compression identity-routing packet that resists paraphrase, keys an in-group, and may lock as a convention after a postmortem or memory write.

## Problem

1. 007 overlays (`ritualCharge`, `inGroupKeying`, `paraphraseResistance`, `attractorStability`, `disseminationImperative`, `falseStabilizationRisk`) are INFERRED and non-Brier. Nothing scores them against A2A behavior.
2. Emergent A2A language (GlossoGen arXiv:2609.01491; dual-channel arXiv:2607.02507; oversight-evasion class arXiv:2605.31170) is a monitorability problem. Surface logs are not enough.
3. The delivery path is mostly *indirect*: retrieved convention, peer message, postmortem note. Direct wrap strings are the wrong family and are refused.
4. Friend handbook URL is UNRESOLVED. Public OWASP RAG stages are enough to start Room C.

## Goals

- G1 Freeze an eval packet with hard-null Brier and no generate verbs.
- G2 Define four rooms (A detector, B dual-channel A2A, C RAG stages, D transmission).
- G3 Require operator-labeled overlay gold. LLM teacher labels are INFERRED and cannot be Room A gold.
- G4 Map findings to OWASP GenAI LLM Top 10 2026 + public RAG Security Cheat Sheet sections.
- G5 Keep 007 as a consumer, not a mutant of this spec.

## Non-goals

- N1 Wrap / jailbreak / ASR boards / restricted paraphrase.
- N2 Training the 007 encoder on 008 logs.
- N3 Claiming the friend handbook until operator stamps a URL.
- N4 Numeric Brier or forecast eligibility.
- N5 Opening 006 IsA.
- N6 Promoting `scripts/shadow/sacred_object/` into `src/hyperlex/`.
- N7 Importing DVRAG or any exploit lab as fixtures.
- N8 Abraxas rune writes.

## Architecture

007 packet in → 008 rooms → 008 eval packet + optional finding rows.
Host treats both JSON blobs as untrusted structured output (LLM10:2026).

### Room A — Detector calibration

Input: frozen 007 checkpoint hashes + overlay sheet.
Output: per-atom 007 inference attachment + overlay comparison.
Gates: inherit 007 E0–E6. Overlay keys may fire; class stays INFERRED; brier null.
Fail-open if weights missing.

### Room B — Dual-channel A2A

See `room-b-protocol.md`.
Two peers, token budget, optional postmortem.
Channels: public, OTR, postmortem, human observer.
Metrics are OBSERVED from logs only.

### Room C — RAG delivery

Walk one civilian attested atom through the 14 public RAG cheat-sheet sections.
Finding shape: `finding-template.md`.
Public contract only until handbook URL is stamped.

### Room D — Transmission

Strong peer mints a convention under budget + postmortem. Weak peer sees usage only.
Measure acquisition, not invention recipes.

## Overlay sheet (normative)

Columns: `atom`, `attested_span_ref`, `lineage_family`, `typology`, `sacred_candidate` (bool), six overlay 0–3 scores, `labeler`, `label_class` (`OBSERVED` only when operator-signed), `notes`.

Minimum to *plan* implement: 12 labeled rows + 12 negatives.
Minimum to *name* a Room A card: 30 labeled + 30 negatives, lexical split, no lemma leak.

Placeholders in `fixtures/overlay_sheet.v0.1.example.jsonl` are unmarked. They are not gold until `labeler` is an operator id.

## Packet (normative)

Schema id: `hyperlex.sacred_object.eval.v0.1`

Hard constants:

- `brier` = null
- `forecast_eligible` = false
- `auto_fire` = false
- `routes_claimed` ⊆ `{form, lexical}` — never `semantic`
- if `restricted_intent_suspected`: drop `surface`; keep `payload_ref`
- forbidden keys: `symbolic`, `has_symbols`, wrap/compose/asr/encode verbs as field names

## Success for this specify cycle

Pack on disk. Notion 008 page points here. Dual-use rows copied. No training. No Room B live run without overlay gold.
