# Clarify 007 — Hyperlexical model

Locked 2026-09-09. Do not reopen without operator amendment.
Amendment A1 (same day): C6/C24 ceiling 150M.

| ID | Question | Lock |
|----|----------|------|
| C1 | Encoder or generative first? | Encoder + heads first. Generative LoRA is a later spec or a later unit after T13. |
| C2 | Where does code live in v0.1? | `scripts/shadow/hyperlexical/` only. No `src/hyperlex/` until operator T13. |
| C3 | May this spec touch API_V1? | No. |
| C4 | May open analysis claim `semantic`? | No. Spec 005. `routes_claimed` ⊆ {form, lexical}. |
| C5 | When is the name Hyperlexical allowed on a Hub card? | Only after eval gate E2 (unbind beats Spec 004 probe). Until then: `hyperlex-encoder-*`. |
| C6 | Parameter ceiling for v1 product? | T1 ≤ **150M** encoder (A1). No 7B product card. T2 decoder not in implement U1. Spark capacity is not a reason to inflate T1 past 150M. |
| C7 | Does the model emit Brier? | No. Hard-null. Stage is INFERRED ordinal. |
| C8 | Role schemes? | Only `positional` and `type_slot` from 004. No third scheme in v0.1. |
| C9 | Dataset in this repo? | Civilian fixtures + schema + split rules. No weight binaries. No restricted corpora. |
| C10 | 006 IsA? | Untouched. This is 007. |
| C11 | Hugging Face publish? | Operator gate. Specs do not self-upload. |
| C12 | Analyze integration? | Optional fail-open attachment. Missing weights ≠ analyze crash. |

## Additive locks from research fold 2026-09-09

| ID | Question | Lock |
|----|----------|------|
| C13 | NeuSOGA synthesis in 007? | No. DISCOVER-shaped encoder only. |
| C14 | Third role scheme? | Abort. No success packet. |
| C15 | `symbolic` / `has_symbols` keys? | Forbidden. |
| C16 | U1b frozen Qwen dump? | Held. Hash embed is control-only. |
| C17 | Graded is-a / HyperLex-2016 head? | No. That is 006. Pointer only. |
| C18 | Sacred overlays as loss or Brier? | No. Optional non-Brier keys only. |
| C19 | MODEL_EMBEDDING without hashes? | Omit analyze block. Fail-open. |
| C20 | LLM-generated slang as E2 gold? | No. Wu/Sun misalignment. |

## Additive locks — Spark + uncensored 2026-09-09

| ID | Question | Lock |
|----|----------|------|
| C21 | Home train/serve box? | NVIDIA DGX Spark (GB10, 128 GB unified, aarch64, `sm_121`). See `hardware.md`. |
| C22 | Uncensored means? | Base encoder. No chat template. No refusal head on civilian slang. See `uncensored.md`. |
| C23 | Safety-tuned instruct trunk allowed as T1? | No. Teacher-only if used at all, and not under the Hyperlexical name. |
| C24 | Use Spark 200B ceiling for the product card? | No. T1 stays ≤**150M** (A1). |
| C25 | NVFP4 required to ship T1? | No. Optional export later. |
| C26 | Dual-use wall removed because uncensored? | No. Detector over generator. No wrap verb. |
| C27 | Orin Nano as train home this cycle? | No. Infer-later only. |
