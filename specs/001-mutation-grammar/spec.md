# Spec 001 — Adversarial Slang Mutation Grammar (first-class Hyperlex)

**Feature**: Detector-side mutation grammar  
**Date**: 2026-09-04  
**Status**: SPECIFY + CLARIFY locked / SHADOW  
**Depends on**: spec 000, constitution v1.0.0  
**Clarify**: `clarify.md` (C1–C10 locked)  
**Companion docs**: `threat-model.md`, `owasp-mapping.md`, `plan.md`, `tasks.md`, `checklist.md`  
**Schema**: `schemas/mutation_trace.v0.1.schema.json`  
**Notion distillation**: https://www.notion.so/3d23e8ba2f5c81a88e52c26942bc1fad

## Intent
Slang is a productive grammar. Hyperlex already labels historical branches and predicts civilian next surfaces. This spec makes **operator-stack detection** first-class so the engine can see when the *rule* moves faster than the *lexicon*.

This is instrumentation for cultural language and for *linguistic* prompt-injection surfaces (OWASP LLM01:2026). It is not a guardrail product and not a jailbreak kit.

## Problem
1. Lineage `branch_operator` describes finished history.
2. `mutation_prediction.v1` proposes future forms of a slang atom.
3. Neither traces stacked rewrites on an attested span.
4. Neither separates lexicon-hit rate from novel-rule rate (Goodhart).
5. Safety literature shows style, dialect, language-games, and phonetic/code-mix change refusal behavior. Treating that as a word list is how patches age out.

## Goals
- G1 Parse attested civilian text into a typed operator stack.
- G2 Persist a receipt-safe packet with frozen integrity rules.
- G3 Expose watch metrics that cannot be satisfied by memorizing last quarter's tokens.
- G4 Keep prediction and detection in separate modules with a hard wall on restricted spans.
- G5 Be reviewable by LLM application-security practitioners: OWASP map, threat model, dual-use bound, epistemic labels.

## Non-goals
- N1 Generate restricted-intent paraphrases, language-game encodings of disallowed requests, or “working wraps.”
- N2 Report attack success rate (ASR) against any model.
- N3 Close LLM01. Detection ≠ mitigation.
- N4 Auto-execute tools, crons, or Abraxas runes from a watch_score (LLM03).
- N5 Rewrite `mutation.py` into an adversarial composer.
- N6 Put hyperstition loop on the detector enum (C3).
- N7 Merge REGISTER_SHIFT and FRAME_WRAP (C2).
- N8 Forecast / Brier on grammar packets (C7).
- N9 SUAS operational evasion guidance.
- N10 Live red-team corpora in this repository.

## Users
- Hyperlex operator studying emergence (primary).
- Abraxas ECO / Companion consuming SIGNAL REPORT mutation traces (advisory).
- Reviewers who need a clean dual-use story.

## In scope (v0.1)
See clarify C5. Schema, enum, packet, L2/L3/L5 parser, COMPOSE aggregator, watch_score, watcher pair, analyze attachment, CLI `mutation-trace`, civilian fixtures, restricted redaction rule, docs.

## Out of scope (v0.1)
GAME_ENCODE parser, CODE_SWITCH parser, FRAME_WRAP parser beyond a boolean `dissociation_flag` heuristic if cheap, SAE steering, multi-model evals, COMPOUND enum, L0 normalizer productization.

## Operator taxonomy (normative)
Ten detector ops, locked (C1).

| Op | Layer | Detect v0.1 | Generate (predict module) | Notes |
|----|-------|-------------|---------------------------|-------|
| SUBSTITUTE | L3 | family / algospeak table | no | cant/algospeak synonym |
| AFFIX | L2 | suffix table | derivational (civilian atom only) | productive morphology |
| CLIP_BLEND | L2 | no | platform_compression adjacent | later |
| EGGCORN | L3 | fixture list | no | folk reanalysis |
| PHONETIC_WARP | L1 | no | vowel-drop on slang atoms only | later for detect |
| GAME_ENCODE | L4 | no | **never** | detect-only when shipped |
| REGISTER_SHIFT | L5 | heuristic | irony templates on slang atoms | not FRAME_WRAP |
| CODE_SWITCH | L6 | no | **never** as generator | detect-only when shipped |
| FRAME_WRAP | L7 | flag only | **never** as generator | distinct from register |
| COMPOSE | ≥2 ops | yes | n/a | aggregator |

Irony is a **feature** (`irony_flag`), not an op. Hyperstition stays in Phase 5.

Each op is conceptually `(layer, polarity, arity, productivity, dual_use)`. Polarity DETECT vs GENERATE is enforced by module boundary, not by comment.

## Packet (normative)
Schema id: `hyperlex.mutation_trace.v0.1`  
File: `schemas/mutation_trace.v0.1.schema.json`

Hard constants:
- `forecast_eligible` = false
- `brier` = null
- if `restricted_intent_suspected`: `payload_ref` required; `surface_span` and `canonical_gloss` null in persisted form

`class` rules: threat-model epistemic section.

Sacred overlays optional and non-Brier: ritualCharge, inGroupKeying, paraphraseResistance, attractorStability, disseminationImperative, falseStabilizationRisk.

## Watch score (normative sketch)
Not a probability. INFERRED instrumentation.

```
watch = clip01(
    0.35 * decode_confidence
  + 0.15 * min(n_ops, 4) / 4
  + 0.20 * register_w          # none=0 low=0.33 med=0.66 high=1
  + 0.10 * irony_flag
  + 0.15 * affix_productivity   # 1 if suffix in productive family table
  + 0.15 * (0 if lexicon_hit and n_ops==1 else 1)
)
```

Do not interpret watch_score as P(jailbreak) or P(adoption).

## Watcher pair (Goodhart)
- **A** lexicon_hit_rate on known family terms + civilian algospeak table over a window.
- **B** novel_operator_rate: new affix-stem pairs, new eggcorn fixtures needed, unseen game-rule markers.

A↑ B flat → overfitting yesterday's words.  
B↑ A flat → grammar moving. That is the instrumentation analog of a moving 0day. It is not an exploit claim.

## Functional requirements
- F1 Civilian affix or table hit → packet with ops + layers.
- F2 Offline parse in v0.1.
- F3 No numeric Brier on the block or packet.
- F4 Must not call `predict_mutations` on restricted-flagged spans.
- F5 Analyze MAY attach `analysis.mutation_trace`; omit if no ops.
- F6 Restricted redaction as C6.
- F7 Tests: benign fixtures only (`rizz`, `unalive`, `it's giving`, `-maxxing`, classic eggcorns).
- F8 Predict module unchanged in role.
- F9 Schema validates; restricted-true fixtures fail if surface persisted.
- F10 CLI prints JSON; exit 0 on empty operators with empty packet or omit.
- F11 No network in unit tests.
- F12 Hosts documented: treat JSON as untrusted output (LLM10).

## Analyze attachment shape
```json
"analysis": {
  "mutation_trace": {
    "schema": "hyperlex.mutation_trace.v0.1",
    "operators": ["REGISTER_SHIFT", "AFFIX", "COMPOSE"],
    "layers_touched": ["L5", "L2"],
    "brier": null,
    "forecast_eligible": false,
    "class": "INFERRED"
  }
}
```
Full packet fields allowed. Restricted redaction applies before receipt emit.

## Acceptance examples (civilian)
Input: `it's giving mid rizz`  
Expect: REGISTER_SHIFT and/or AFFIX/SUBSTITUTE family hit on `rizz`; COMPOSE if ≥2; `brier` null; `forecast_eligible` false.

Input: `unalive`  
Expect: SUBSTITUTE or algospeak_flag; lexicon_hit likely true.

Input: empty / ordinary prose without slang  
Expect: omit block or empty operators.

## Risks and mitigations
| Risk | Mitigation |
|------|------------|
| Dual-use generator creep | C4, F4, N1, module split |
| Receipt cookbook | C6 |
| False OBSERVED on heuristics | epistemic rules |
| Watch Goodhart | pair A/B |
| Agency bleed | C10 |
| Scope cosplay as guardrail | owasp-mapping honest limitation |

## Success
Clarify C1–C10 recorded. Schema in repo. Checklist pass. Operator review of constitution VII–X. Implement still a later cycle.

## References (provenance, not payloads)
- OWASP GenAI LLM Top 10 2026 (LLM01 primary; LLM03 agency; LLM10 output handling)
- MITRE ATLAS AML.T0054
- arXiv:2511.10519 linguistic style jailbreaks
- arXiv:2604.21152 dialect vs demographics / dialect jailbreak
- arXiv:2411.12762 language games
- arXiv:2505.14226 phonetic code-mix
- arXiv:2405.00718 dark jargon
- arXiv:2603.26236 informal-register SAE
- Hyperlex `docs/slang-lineages.md`, `src/hyperlex/analysis/mutation.py`
