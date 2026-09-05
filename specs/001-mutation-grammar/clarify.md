# Clarify lock — Spec 001

**Date:** 2026-09-04  
**Status:** LOCKED for v0.1  
**Gate:** `/speckit.clarify` complete. Implement may not reopen these without an amendment row.

## Decisions

| ID | Question | Decision | Rationale |
|----|----------|----------|-----------|
| C1 | Detector enum size | Keep the ten ops. Do not add COMPOUND, HYPERSTITION, or L0-only ORTHOGRAPHIC in v0.1. | Compound is generation or COMPOSE+SUBSTITUTE. Hyperstition is Phase 5 actualization, not a rewrite rule. L0 stays inside PHONETIC_WARP / platform_compression until a dedicated normalizer exists. |
| C2 | Irony | Do **not** merge into one bucket. REGISTER_SHIFT = speech-act / affect. FRAME_WRAP = why-said / lore / dissociation. `irony_flag` is a feature, not an operator. | Style jailbreaks and “just the lore” wraps are different mechanisms. Merging smears watch_score. |
| C3 | Hyperstition | Stay off the parse enum. Remain Phase 5 / `forecast_hyperstition_risk`. | Different object: narrative actualization vs surface rewrite. |
| C4 | Predict vs detect | `mutation_prediction.v1` stays civilian next-forms of slang atoms. `mutation_trace.v0.1` never calls predict on a span with `restricted_intent_suspected`. | Constitution VII. |
| C5 | v0.1 parse layers | L2 AFFIX, L3 SUBSTITUTE (+ eggcorn fixtures), L5 REGISTER_SHIFT heuristic, COMPOSE if ≥2. | Highest cultural signal, lowest dual-use. |
| C6 | Restricted storage | If flag true: persist `payload_ref` (SHA-256 of normalized surface) only. Drop `surface_span` and `canonical_gloss` from receipt body. | Prevents the detector from becoming a wrap archive. |
| C7 | Brier / forecast | `brier` null. `forecast_eligible` false. Watch scores are instrumentation, not probabilities of harm or adoption. | Constitution III. |
| C8 | OWASP posture | Map operators to OWASP GenAI LLM Top 10 **2026** as *coverage of detection surface*, not as a claim that Hyperlex is a guardrail product. | Honest scope. |
| C9 | Examples | Civilian / linguistic only in-repo. No restricted how-to strings. Cite papers by id. | Dual-use + reviewability. |
| C10 | Agency | Mutation-trace output MUST NOT trigger tools, relays that execute, or cron. Advisory envelopes only. | OWASP LLM03 Excessive Agency. |

## Deferred (explicit non-locks)
- Formal SAE informal-register feature as `register_shift` source.
- Live multi-model eval of register-skewed refusal (research fork, not this package).
- COMPOUND as its own enum value.
- GAME_ENCODE / CODE_SWITCH parsers.
