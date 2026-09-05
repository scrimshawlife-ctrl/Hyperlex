# Spec 001 — Adversarial Slang Mutation Grammar (first-class Hyperlex)

**Feature**: Detector-side mutation grammar  
**Date**: 2026-09-04  
**Status**: SPECIFY / SHADOW  
**Depends on**: spec 000, constitution v1.0.0  
**Notion distillation**: https://www.notion.so/3d23e8ba2f5c81a88e52c26942bc1fad

## Intent
Treat slang mutation as a *productive grammar*, not only a next-form lottery. Hyperlex already predicts civilian next surfaces. This spec adds first-class **parse → tag operators → packet → receipt → watch**, so the engine can see when the *rule* is moving faster than the *lexicon*.

## Problem
- Lineage `branch_operator` labels history.
- `mutation_prediction` proposes future *forms*.
- Neither scores operator *stacks* on an observed span, nor separates lexicon-hit from novel-rule rate, nor binds dual-use storage rules.
Safety literature shows register, dialect, style, game-encode, and phonetic warp shift model behavior. Hyperlex may instrument that as watch-language. It may not implement an exploit factory.

## In scope
1. `SlangMutationPacket.v0.1` schema.
2. Operator enum aligned with lineage docs plus detector-only classes.
3. Layer tags L0–L8.
4. `watch_score` (not Brier).
5. Module `hyperlex.mutation.grammar` (or `hyperlex.analysis.mutation_grammar`) — parse attested text.
6. Lineage DAG edges for operator stacks (`hyperlex.mutation.lineage`).
7. Watcher pair: lexicon hit rate vs novel-operator rate.
8. Analyze attachment `analysis.mutation_trace` (additive, API_EXTENDED).
9. CLI `mutation-trace` (offline).
10. Benign fixtures only (OSD-like / existing family terms / eggcorns / algospeak civilians).
11. Hash-only storage when `restricted_intent_suspected`.

## Out of scope
- Generating restricted wraps or jailbreak recipes.
- Changing `mutation_prediction` into an adversarial composer.
- Forecast eligibility / Brier on grammar packets.
- New Abraxas runes.
- Live red-team against third-party models.
- SUAS operational evasion guidance.

## Operator enum (detection)
`SUBSTITUTE | AFFIX | CLIP_BLEND | EGGCORN | PHONETIC_WARP | GAME_ENCODE | REGISTER_SHIFT | CODE_SWITCH | FRAME_WRAP | COMPOSE`

Map to existing prediction/lineage ops where overlap exists:
- AFFIX ≈ derivational
- CLIP_BLEND / PHONETIC_WARP / L0 ≈ platform_compression
- EGGCORN = eggcorn
- REGISTER_SHIFT / FRAME_WRAP ⊃ irony_inversion + style
- COMPOSE = stacked operators (new as explicit type)

## Packet (normative fields)
- `schema`: `hyperlex.mutation_trace.v0.1`
- `packet_id`, `observed_at`, `source`
- `surface_span`, `recovered_lemma` (nullable), `canonical_gloss`
- `operators[]` ordered enum
- `layers_touched[]` L0–L8
- `register_shift` none|low|med|high
- `irony_flag`, `dissociation_flag`, `algospeak_flag`, `machine_dialect` bool
- `affix_family` nullable
- `decode_confidence` 0–1 INFERRED
- `lexicon_hit` bool
- `watch_score` 0–1 INFERRED (not Brier)
- `class` OBSERVED|INFERRED|SPECULATIVE
- `restricted_intent_suspected` bool
- `payload_ref` nullable hash; required if restricted flag
- `forecast_eligible` MUST be false
- `brier` MUST be null
- `provenance[]`, `receipt_id` nullable
- sacred overlays optional: ritualCharge, inGroupKeying, paraphraseResistance, attractorStability, disseminationImperative, falseStabilizationRisk

## Watch score (normative sketch)
`watch = clip01(decode_confidence + 0.15*n_ops + register_shift_w + irony + affix_prod - lexicon_only)`
High watch + restricted flag → SHADOW alert, no auto-execute, no reconstructable wrap.

## Watcher pair (Goodhart)
- A: lexicon hit rate on known family terms / algospeak table
- B: novel-operator rate (unseen affix, new game rule, new eggcorn)
A↑ B flat = overfitting last quarter. B↑ A flat = grammar moving (0day condition as *instrumentation*, not as attack success).

## Functional requirements
- F1. Given civilian text containing an attested affix or eggcorn, emit a packet with operators and layers.
- F2. Offline only for v0.1 parse.
- F3. Must not attach numeric Brier.
- F4. Must not call mutation_prediction to fill restricted spans.
- F5. Analyze MAY include `mutation_trace` when parse returns operators; omit block if empty.
- F6. Restricted flag true → drop `surface_span` from persisted receipt body; keep hash.
- F7. Tests use only benign fixtures (`rizz`, `unalive`, `maxxing` as affix family, eggcorn phrases).
- F8. Prediction module remains available and remains SPECULATIVE next-forms of *slang atoms*, not of restricted requests.

## Success
- Schema file + pytest for packet validation.
- Offline `mutation-trace "it's giving mid rizz"` returns COMPOSE/AFFIX/REGISTER_SHIFT tags, brier null, forecast_eligible false.
- Constitution VII–X satisfied on review.
