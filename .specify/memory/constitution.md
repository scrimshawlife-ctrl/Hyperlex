# Project Constitution: Hyperlex

**Version**: 1.0.0  
**Ratified**: 2026-09-04  
**Last Amended**: 2026-09-04  
**Status**: SHADOW / ADVISORY until operator promotion  
**Remote**: scrimshawlife-ctrl/Hyperlex  
**Notion owner**: Hyperlex spine (01 Specs & Spines)

This constitution is the evaluation gate for every later Spec Kit artifact (`specify`, `plan`, `tasks`, `implement`, `converge`). Existing `DESIGN.md`, `SPEC.md`, `SKILL.md`, and `docs/api-v1.md` remain runtime truth until an implement cycle lands. This file does not mutate API_V1.

## Principles

### I. Catch becoming-culture, not settled culture
Hyperlex exists to catch language while it is still becoming culture. Lineage, receipts, and settlement are first-class. Lexicon dumps without operator and mutation structure are incomplete.

### II. Offline-first, fail-closed on scores, fail-open on ingest
Baseline analysis MUST run under `HYPERLEX_OFFLINE=1` / `source=mock` with no network. Ingest failures degrade. Missing settlements yield `NOT_COMPUTABLE`. Never crash the analyze path for optional enrichers.

### III. Settled Brier only
Open analysis, Phase 5, mutation prediction, and mutation-grammar watch scores MUST keep `brier: null`. Numeric Brier exists only after operator settlement on an eligible forecast class. Mutation-grammar packets are never forecast-eligible.

### IV. Provenance discipline
Every claim is `OBSERVED`, `INFERRED`, or `SPECULATIVE`. Lineage confidence is INFERRED. Next-form prediction is SPECULATIVE. Operator-stack detection on an attested surface may be OBSERVED for the surface and INFERRED for the stack.

### V. No Abraxas hard import
Hyperlex MUST NOT import Abraxas. Wire shapes live under `hyperlex.compat.abraxas` as export-only. Hyperlex MUST NOT write Abraxas rune registry rows, p89 binds, or Forecast spines.

### VI. Receipt integrity is frozen history
Lineage backprop, mutation traces, and grammar overlays MUST NOT rewrite historical receipt hashes or `provenance.integrity`.

### VII. Detector over generator for adversarial grammar
Mutation *prediction* may emit civilian next surface forms of a slang atom (existing `hyperlex.mutation_prediction.v1`). Mutation *grammar* (this expansion) is a detector, tracer, and watcher. It MUST NOT generate restricted-intent wraps, jailbreak recipes, or reconstructable payloads when `restricted_intent_suspected` is true. Store hash + layer tags only in that case.

### VIII. Human sovereignty on promotion
Schema landings, registry family adds, Chroma promotes, cron registration, and canon status changes require an operator gate. Specs do not self-promote.

### IX. Library-first additive modules
New capability ships as a package module (`hyperlex.analysis.*` or `hyperlex.mutation.*`) with tests before CLI sugar. API_V1 stays frozen; additive symbols go on `API_EXTENDED`.

### X. Dual-use bound
Cite safety literature. Do not reproduce restricted payloads. SUAS/SS may consume watch-language tags only. No operational evasion playbook in this repo.

## Constraints
- Python ≥ 3.10, stdlib-first baseline.
- Atomic terms; do not density-stack multi-term bags as one seed by default.
- RUNE.HLX.* envelopes are advisory. No execute_production.
- Sacred-slang metrics (ritualCharge, paraphraseResistance, …) are overlays, not Brier inputs.

## Amendment
Operator amends this file, bumps version, restamps Last Amended. Dependent specs must re-check principles I–X.
