# Clarify 007 — Hyperlexical model

Locked 2026-09-09. Do not reopen without operator amendment.

| ID | Question | Lock |
|----|----------|------|
| C1 | Encoder or generative first? | Encoder + heads first. Generative LoRA is a later spec or a later unit after T13. |
| C2 | Where does code live in v0.1? | `scripts/shadow/hyperlexical/` only. No `src/hyperlex/` until operator T13. |
| C3 | May this spec touch API_V1? | No. |
| C4 | May open analysis claim `semantic`? | No. Spec 005. `routes_claimed` ⊆ {form, lexical}. |
| C5 | When is the name Hyperlexical allowed on a Hub card? | Only after eval gate E2 (unbind beats Spec 004 probe). Until then: `hyperlex-encoder-*`. |
| C6 | Parameter ceiling for v1 product? | T1 ≤ 130M encoder. No 7B. T2 decoder not in implement U1. |
| C7 | Does the model emit Brier? | No. Hard-null. Stage is INFERRED ordinal. |
| C8 | Role schemes? | Only `positional` and `type_slot` from 004. No third scheme in v0.1. |
| C9 | Dataset in this repo? | Civilian fixtures + schema + split rules. No weight binaries. No restricted corpora. |
| C10 | 006 IsA? | Untouched. This is 007. |
| C11 | Hugging Face publish? | Operator gate. Specs do not self-upload. |
| C12 | Analyze integration? | Optional fail-open attachment. Missing weights ≠ analyze crash. |
