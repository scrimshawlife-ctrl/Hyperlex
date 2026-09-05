# Spec 000 — Hyperlex Spine (as-built, SDD lock)

**Feature**: Hyperlex system specification  
**Date**: 2026-09-04  
**Status**: SPECIFY (retroactive lock of v0.4.0 behavior)  
**Constitution**: `.specify/memory/constitution.md` v1.0.0  
**Runtime version described**: 0.4.0 (main @ 3e66637)

## Why this spec exists
Hyperlex already ships. It did not start as Spec Kit. This document is the constitution-gated *what/why* lock so later features (including 001 mutation grammar) evaluate against a single spine instead of drifting off README + STATUS.

## User / operator intent
An operator needs a local, receipt-backed engine that:
1. Ingests a query from mock or live sources.
2. Detects neologisms, lineage family, virality, memetics, hyperstition stage.
3. Emits integrity-hashed receipts.
4. Extracts forecasts with `brier: null`.
5. Settles those forecasts under human authority and only then scores Brier series.
6. Optionally simulates cultural transmission (Phase 5, SPECULATIVE).
7. Optionally predicts next civilian surface forms (`mutation_prediction`, SPECULATIVE).
8. Never depends on Abraxas at import time.

## In scope (current surface)
- Intake adapters + cache + rate limit (`mock` required).
- `detect_memetic_patterns` analysis contract: `observed` / `inferred` / `speculative`.
- `match_lineage` + confidence threshold 0.42 + `score_breakdown`.
- Receipts + hash-chained ledger.
- Forecast extract → settle → score-series.
- Phase 5 simulation packets (`hyperlex.phase5_scenario.v1`), brier null.
- Lineage backfill packs + non-mutating backprop.
- `analysis.mutation_prediction` (`hyperlex.mutation_prediction.v1`).
- Compat export under `hyperlex.compat.abraxas`.
- Hermes skill contract (`SKILL.md`) + CLI (`scripts/hyperlex.py`, `python -m hyperlex`).

## Out of scope
- Public PyPI.
- Hard Abraxas / Forecast / HollerSports writes.
- Auto-settle, auto-cron, auto-registry promotion.
- Adversarial wrap generation (see spec 001).
- Smash-merge with Abraxas-v2.0 doctrine repo.

## Requirements
- R1. Offline analyze MUST succeed without network.
- R2. Open analysis MUST set `provenance.brier` / block `brier` to null.
- R3. Settlement MUST require an authority marker (TRUE|FALSE|VOID).
- R4. Backprop MUST NOT rewrite receipt integrity.
- R5. API_V1 symbols MUST remain unchanged by additive work.
- R6. Claims MUST be labeled OBSERVED / INFERRED / SPECULATIVE.
- R7. Fail-closed on missing settlements (`NOT_COMPUTABLE`).
- R8. Fail-open on optional LLM / live ingest.

## Existing mutation operators (lineage docs)
Documented in `docs/slang-lineages.md`:
extra-grammatical formation, sense extension, irony inversion, platform compression, eggcorn / folk etymology, cross-family borrowing, hyperstition loop.

Prediction vocabulary in `hyperlex.mutation_prediction.v1`:
`platform_compression`, `derivational`, `irony_inversion`, `compound_phrase`, `sense_extension`, `cross_family_borrowing`, `extra-grammatical`.

Spec 001 extends this vocabulary for *detection* without replacing prediction.

## Success (spine)
- `python3 scripts/hyperlex.py doctor` and `smoke` green offline.
- This spec plus constitution are the SDD entry points for Hyperlex work after 2026-09-04.
