# Research fold 007 — what transfers, what does not

**Date**: 2026-09-09
**Lane**: SHADOW / advisory
**Rule**: OBSERVED pages first. No Wiki compile. No rune bind. No Hyperlex settle.

This file is the specify-cycle fold of operator Notion research into Spec 007. It does not reopen 004, 005, or 006.

## Sources consulted (OBSERVED)

| Page | ID | Use |
|------|----|-----|
| Neuro-Symbolic Distill — NeuSOGA + Emergent TPR | `3d63e8ba-2f5c-8188-9068-cef65d128781` | DISCOVER vs synthesis split |
| Inbox atom RECOVERABLE_SYMBOLIC_STRUCTURE | `3d63e8ba-2f5c-81aa-9de9-e1d856f41c3c` | trigger only |
| Spec / Plan / Converge 004 | `3d63e8ba-2f5c-814c-92a9-c76b0d89d390` et al. | unbind baseline + hard gates |
| Hyperlexic reasoning survey v1 | `3d63e8ba-2f5c-810a-8682-c7cc3fe3b6f6` | C1–C3 name + eval holds |
| C1 clinical hyperlexia ≠ reasoner | `3d63e8ba-2f5c-8147-974b-d2164f85947d` | cheap-decode analogue |
| C2 HyperLex-2016 graded LE | `3d63e8ba-2f5c-81aa-835e-e6b48766969d` | belongs to 006 IsA, not 007 heads |
| C3 name collisions + U1b hold | `3d63e8ba-2f5c-81b7-a46f-ec04b99b37ec` | Qwen dump held; ngram control-only |
| Spec 005 route labels | `3d63e8ba-2f5c-8155-9c29-ddf5e9e33153` | no `semantic` |
| Slang-as-Sacred Object 2026-09-03 | `3d03e8ba-2f5c-81e6-9eaa-dd24e24e4c24` | overlays ≠ Brier; Wu/Sun misalignment |
| Mutation grammar distillation 2026-09-04 | `3d23e8ba-2f5c-81a8-8e52-c26942bc1fad` | detect wall |
| HollerSports Latent Context v2.4 | `34d3e8ba-2f5c-813e-97ca-e0de6c982f11` | embedding provenance fields |
| TimesFM × slang join card | `3d33e8ba-2f5c-8101-831d-f1f85b90eaa2` | TimesFM is not slang truth |

Papers named on those pages (citations, not payloads):

- arXiv:2609.01408 NeuSOGA
- arXiv:2608.29530 Emergent Symbolic Structure / DISCOVER
- arXiv:2301.12987 Bennett weakest-not-shortest (selection_proxy stamp)
- arXiv:1608.02117 HyperLex graded LE
- Ostrolenk 2017 hyperlexia review
- arXiv:2509.15518 Wu/Sun human vs machine slang
- constitution VII–X + 001 dual-use wall

## Transfers into 007 (normative)

### T1 DISCOVER, not NeuSOGA synthesis

007 is a **discovery** encoder: recover role–filler structure from a bound representation of an attested slang atom.

007 is **not** NeuSOGA. NeuSOGA builds explicit geometric symbols from observations (synthesis). Importing that stack would be a different spec and would touch vision/geometry surfaces Hyperlex does not own.

### T2 Inherit 004 hard gates

From Spec 004 / Plan 004 / Converge 004:

- schemes: `positional`, `type_slot` only. Third scheme name aborts.
- no boolean key `symbolic` / `has_symbols`. Interpretation “has structure” is INFERRED and stays out of those key names.
- `selection_proxy` is a stamp (`weakness` | `mdl` | `unspecified`), not an optimizer.
- no network in unit tests.
- no rune write, no settle write.

### T3 E2 baseline is the 004 fixture card (OBSERVED)

Converge 004 receipts on Hyperlex main `f8f0ef0` / PR #17:

- positional: `test_mse=0.0000`, `swap=1.000`, `hit=True`
- type_slot: `test_mse=1.6377`, `swap=0.438`
- Brier null
- accepted gap: **fillers not learned**; atomic fixture is sequence-atom

007 T1 is allowed to **learn fillers**. That is the only 004 gap 007 is allowed to close. E2 still has to beat this card on the shared fixtures. A model that only matches the white-box positional toy (mse=0) has not earned the Hyperlexical name.

### T4 U1b frozen-Qwen dump stays HELD

C3: U1b Qwen dump held. Hash-ngram embed is **control-only**, not a reasoner.

007 U1 stub may use `STATIC_HASH_EMBEDDING` as the CI fallback. That path MUST set `model_id=stub` and MUST NOT be described as Hyperlexical structure.

A later live frozen encoder (004 U1b) is a different operator sentence. 007 does not sneak it in.

### T5 Clinical analogue is decode ≠ settle

C1: hyperlexia = advanced decoding vs lagging comprehension. Analogue for this packet: surface operators and lineage heads may fire cheap; `brier` stays null; settlement stays human.

Do not market 007 as a reasoning LLM.

### T6 Graded is-a is 006, not a 007 head

C2: HyperLex-2016 (2616 graded LE pairs) is a future **eval spec**. Similarity winners on SimLex drop there. Hyperlex repo has no graded is-a eval yet.

007 MUST NOT add an `isa_score` head in v0.1. Pointer only. Opening that eval is **specify 006**, which this pack still does not open.

### T7 Name collisions

C3: HyPER, HyperGuide, LLM-Hype, HypoSearch, SPLADE-HYPER, clinical hyperlexia, Cambridge HyperLex dataset, French Hyperlex legaltech are different objects.

Hub card and model_id MUST say `hyperlex-encoder-*` / `hyperlex-structure-*` and cite this spec. Do not squat `HyperLex` (2016 dataset) or clinical hyperlexia.

### T8 Sacred overlays stay non-Brier

`ritualCharge`, `inGroupKeying`, `paraphraseResistance`, `attractorStability`, `disseminationImperative`, `falseStabilizationRisk` may appear as optional overlay keys. They are not losses, not E2, not Brier.

Wu/Sun (2509.15518): machine-generated slang is biased vs attested usage. Weak labels from an LLM generator are INFERRED at best and cannot be the E2 gold.

### T9 Embedding provenance

If a non-stub vector is produced, packet MUST carry `model_id`, `embed_mode`, `input_hash`, `vector_hash`.

`embed_mode`: `STATIC_HASH_EMBEDDING` | `MODEL_EMBEDDING`

Missing provenance on a MODEL_EMBEDDING path → omit the analyze block (fail-open).

Latent similarity MUST NOT create forecasts or fire tools.

### T10 TimesFM / Phase 5 are not gold

TimesFM join card: univariate series priors only. Not slang truth. Phase 5 packets stay SPECULATIVE. 007 does not ingest them as lineage labels.

## Does not transfer

- NeuSOGA code or geometric abstraction runtime
- Abraxas rune registry rows
- HollerSports scoring formulas
- Slang Engine v5 schema mutation
- 004 U2, API_EXTENDED, hlx verb, Noema score
- 005 implement
- 006 IsA
- U1b Qwen weights in this repo
- Wiki compile of the survey chunks
