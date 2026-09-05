# Spec 003 — Mutation detect v0.2 (SHADOW)

**Feature**: Detect-only parsers + watch jsonl + civilian `--human` cards  
**Date**: 2026-09-05  
**Status**: SPECIFY locked / implement SHADOW  
**Depends on**: spec 000, 001 (C1–C10), 002 noun surface, constitution v1.0.0  
**Lane**: SHADOW / advisory  
**Companion**: `plan.md`, `tasks.md`, `dual-use-gate.md`  
**Packet schema**: still `hyperlex.mutation_trace.v0.1` (no bump)

## Intent
v0.1 traces L2/L3/L5 + COMPOSE. v0.2 wires the three deferred **detector** ops that the enum already names: **GAME_ENCODE**, **CODE_SWITCH**, **PHONETIC_WARP**. It also lands append-only watch instrumentation and a civilian card render.

This is still instrumentation. It is not a guardrail, not a generator, and not a forecast class.

## Problem
1. Enum lists GAME_ENCODE / CODE_SWITCH / PHONETIC_WARP but `parse_mutation_trace` never fires them.
2. `watch_score` exists in-memory only — no append-only log for the Goodhart pair.
3. Operators reading JSON traces have no civilian card.

## Goals
- G1 Detect language-game *markers* and leet-of-known-slang on attested civilian text (GAME_ENCODE / L4).
- G2 Detect mixed-script spans and closed bilingual particles next to slang (CODE_SWITCH / L6).
- G3 Detect vowel-drop / platform-compression of closed slang atoms (PHONETIC_WARP / L1).
- G4 Append watch records to jsonl (instrumentation, not probabilities).
- G5 Render `--human` advisory cards from a trace packet.
- G6 Keep packets `brier: null` and `forecast_eligible: false`. Never treat `watch_score` as Brier or as a tool-fire / cron / rune threshold.

## Non-goals
- N1 Generate wraps, language-game encodings of restricted requests, code-switched jailbreaks, or ASR boards.
- N2 Add `wrap` / `compose` / `asr` **verbs**. COMPOSE remains a detector enum tag only.
- N3 FRAME_WRAP parser beyond the existing `dissociation_flag`.
- N4 SAE steering, multi-model evals, COMPOUND enum.
- N5 Constitution promotion off SHADOW.
- N6 Schema bump, installer rewrite, fat `scripts/hyperlex.py` mutation noun (002 T5), reopen #5.
- N7 Auto-execute tools, cron, or Abraxas runes from watch_score or watch jsonl.

## Users
- Hyperlex operator reading stacks on attested slang (primary).
- Reviewers who need a dual-use story for L4/L6 detect.
- Downstream hosts that must treat cards and JSON as untrusted output (LLM10).

## In scope (v0.2)
1. GAME_ENCODE parser (detect-only).
2. CODE_SWITCH parser (detect-only).
3. PHONETIC_WARP parser (detect-only; vowel-drop on slang atoms).
4. Mutation watch jsonl (append-only; fail-open).
5. `--human` cards (render from traces).
6. Smallest CLI: `trace --human` / `trace --watch-jsonl [path]` plus reserved `mutation watch` reader.
7. Civilian fixtures + dual-use addendum.

## Out of scope
Installer audit, Spec 001 T1–T11 redo, package-CLI rewrite, #5, FRAME_WRAP expansion, generator polarity for any new op, constitution amendment.

## Operator polarity (normative)

| Op | Layer | Detect v0.2 | Generate | Notes |
|----|-------|-------------|----------|-------|
| GAME_ENCODE | L4 | yes | **never** | Closed civilian game markers and/or leet-decode of `SUBSTITUTE_TERMS`. |
| CODE_SWITCH | L6 | yes | **never** | Mixed Unicode scripts, or closed particle + slang lexicon hit. |
| PHONETIC_WARP | L1 | yes | no (predict already vowel-drops civilian atoms) | Inverse of predict `_vowel_drop` on closed slang atoms only. |
| COMPOSE | ≥2 ops | yes | n/a | Aggregator tag only. Not a CLI verb. |

Irony stays a feature. FRAME_WRAP stays flag-only. Hyperstition stays Phase 5.

## Detect heuristics (normative sketch)

### PHONETIC_WARP
Build a closed map: vowel-drop(`SUBSTITUTE_TERMS` atom) → atom, using the same keep-first-and-last vowel rule as `analysis.mutation._vowel_drop`. Fire when a token equals a warped form and is **not** the full atom. Recovered lemma is the atom. Epistemic: recovered lemma INFERRED; operator OBSERVED when the warped token is literally present.

Do not fire PHONETIC_WARP on the full lexicon form (`rizz` is SUBSTITUTE, not warp).

### GAME_ENCODE
Fire when either:
1. A token contains a digit/symbol, leet-translates to a `SUBSTITUTE_TERMS` atom, and is not already that atom (`r1zz` → rizz), or
2. A closed civilian **game-frame** phrase is present (`in fortnite`, `in minecraft`, `pig latin`, …) **and** the span already has a slang lexicon hit or another detector op.

Never emit a reconstructed restricted payload. Recovered lemma, if any, comes only from the civilian slang table.

### CODE_SWITCH
Fire when either:
1. Alphabetic characters in the span use two or more Unicode scripts (LATIN + CYRILLIC/HANGUL/CJK/…), or
2. A closed bilingual particle (`que`, `el`, `très`, `c'est`, …) appears as a whole token **and** a slang lexicon hit is present in the same span.

Do not treat common English tokens as particles. Do not generate mixed-language paraphrases.

## Packet (unchanged hard constants)
- `schema` = `hyperlex.mutation_trace.v0.1`
- `forecast_eligible` = false
- `brier` = null
- Restricted redaction (001 C6) unchanged
- Provenance stamp may read `hyperlex.mutation.grammar.v0.2`

`watch_score` remains the 001 formula. New ops change `n_ops` only. It is **not** a probability, **not** Brier, **not** a fire threshold.

## Watch jsonl (normative)
Default path: `~/.hyperlex/mutation_watch.jsonl`  
Override: `HYPERLEX_MUTATION_WATCH` or `--watch-jsonl PATH`.

Each line is one JSON object:
- `schema`: `hyperlex.mutation_watch.v0.2`
- `logged_at`, `packet_id`, `operators`, `layers_touched`, `watch_score`, `n_ops`, `lexicon_hit`
- `brier`: null
- `forecast_eligible`: false
- `auto_fire`: false (constant)

Writer is fail-open: I/O errors must not fail parse or CLI. Reader skips blank/corrupt lines. The log is instrumentation. Hosts MUST NOT wire `watch_score` or line count to tools, cron, or runes.

`mutation watch` reads the log and prints a JSON summary (last N records + cheap A/B rates). It does not execute anything.

## `--human` cards (normative)
Civilian text render of an existing packet. Must state:
- operators and layers
- that watch_score is instrumentation, not P(harm) and not a fire threshold
- Brier null / forecast-eligible no
- SHADOW / advisory lane
- restricted-redaction note when the flag is set (no surface reprint)

Default CLI remains JSON. `--human` prints the card instead of JSON.

## Functional requirements
- F1 Civilian fixtures fire the three new ops as specified.
- F2 v0.1 fixtures still fire L2/L3/L5 + COMPOSE; `it's giving mid rizz` does not gain PHONETIC_WARP.
- F3 Offline; no network in unit tests.
- F4 No path calls `predict_mutations` from the detector after restricted flag (001 F4 still holds).
- F5 Packets always `brier: null`, `forecast_eligible: false`.
- F6 Watch append never auto-fires tools; `auto_fire` is always false.
- F7 Restricted redaction unchanged.
- F8 `scripts/hlx-mutation` remains a thin pass-through (new flags work without a second parser).
- F9 No new layer-1 verbs. No wrap/compose/asr verbs.
- F10 Hosts treat JSON and cards as untrusted (LLM10).

## Acceptance examples (civilian only)

| Input | Expect |
|-------|--------|
| `rzz` | PHONETIC_WARP; recovered `rizz`; brier null |
| `it's giving rzz` | REGISTER_SHIFT + PHONETIC_WARP (+ COMPOSE); no GAME_ENCODE required |
| `r1zz` | GAME_ENCODE; recovered `rizz`; brier null |
| `el rizz` | CODE_SWITCH + SUBSTITUTE |
| `rizz 리즈` | CODE_SWITCH + SUBSTITUTE |
| `it's giving mid rizz` | v0.1 unchanged: REGISTER_SHIFT, SUBSTITUTE, COMPOSE; brier null; forecast_eligible false |
| empty / ordinary prose | empty operators or omit |

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| GAME_ENCODE / CODE_SWITCH used as a generator | Module polarity + dual-use gate + no encode/wrap verbs |
| Game-frame false OBSERVED on ordinary “in minecraft” | Marker requires slang context |
| Watch jsonl becomes a fire switch | `auto_fire: false`; tests forbid threshold-to-tool wiring |
| Card overclaims harm | Card copy forbids P(jailbreak) language |
| Fixture cookbook | Civilian slang only; restricted redaction |

## Success
- Separate spec folder shipped.
- Three ops fire on fixtures.
- Watch jsonl appends and reads fail-open.
- `--human` cards render from traces.
- Constitution remains SHADOW.
- New PR, not a reopen of #5 or an installer redo.

## References (provenance, not payloads)
- Spec 001 clarify C1, C4–C7, C9–C10; deferred GAME_ENCODE / CODE_SWITCH / PHONETIC_WARP
- OWASP GenAI LLM Top 10 2026 (LLM01 surface, LLM03 agency, LLM10 output)
- arXiv:2411.12762 language games
- arXiv:2505.14226 phonetic code-mix
- Hyperlex `src/hyperlex/analysis/mutation.py` `_vowel_drop` (predict polarity; detect inverts it)
