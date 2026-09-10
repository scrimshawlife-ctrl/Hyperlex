# Spec 007 — Hyperlexical model (SHADOW)

**Feature**: Learned recoverable-structure encoder for slang atoms  
**Date**: 2026-09-09  
**Status**: SPECIFY locked C1–C52 / SHADOW implement on main / E2 fail / no Hub  
**Depends on**: constitution v1.0.0 I–X; specs 000, 001, 003, 004; 005 route-labels (do not claim `semantic`)  
**Does not open**: 006 IsA (reserved)  
**Clarify**: `clarify.md` + `locks-a4.md` + `locks-a5.md`  
**Companion docs**: `plan.md`, `tasks.md`, `checklist.md`, `dual-use-gate.md`, `research.md`, `data-model.md`, `dataset-harvest.md`, `hardware.md`, `uncensored.md`, `amendments.md`, `weights.md`, `AARON-SPARK-TRAIN.md`, `hf-package/`
**Schema**: `schemas/hyperlexical_inference.v0.1.schema.json`  
**Lane**: SHADOW / advisory  
**Home (v0.1)**: `scripts/shadow/hyperlexical/` — never `src/hyperlex/` until T13 promote  
**Home box**: NVIDIA DGX Spark (GB10, 128 GB unified, aarch64, `sm_121`)  
**Alignment**: uncensored **base encoder** — no chat template, no refusal head on civilian slang  
**Packet**: `hyperlex.hyperlexical.inference.v0.1`  
**HF name reserved**: `hyperlex-encoder-*` until unbind gate passes; `hyperlex-structure-*` only after gate

## Intent

Hyperlex already matches lineage by registry + local vectors and probes recoverable structure with a stdlib TPR linear transform (Spec 004). Neither is a trained model. This spec defines the **Hyperlexical model**: a small encoder that binds slang as role–filler structure and emits receipt-safe inference packets.

The model exists to beat bag-of-terms and the Spec 004 linear probe on held-out civilian fixtures. It does not replace receipts, settlement, or API_V1.

Train and serve on the operator DGX Spark. Product card stays T1 ≤150M (A1). Spark capacity is not a license to ship a 7B chat LM under this name.

## Problem

1. `match_lineage` is lexical overlap plus optional vector re-rank. It does not unbind roles.
2. Spec 004 proves a DISCOVER probe can recover `positional` / `type_slot` bindings offline. The probe is not learned.
3. Mutation detect (001/003) traces operators on attested spans. It does not embed phylogeny.
4. Phase 5 simulation is SPECULATIVE and Brier-null. A model that emits fake Brier would violate III.
5. A general chat LLM called “Hyperlexical” would fight offline-first, dual-use VII, and library-first IX.
6. A safety-tuned instruct trunk will refuse or rewrite the dialect / informal / sacred atoms this library exists to measure.

## Goals

- G1 Define a frozen inference packet with hard-null Brier and no `semantic` route claim (005).
- G2 Specify encoder-first architecture and parameter ceilings that train on DGX Spark and infer offline / CPU / Spark. T1 stays ≤150M (A1).
- G3 Specify an unbind eval that must beat Spec 004 linear probe before the word Hyperlexical is used on a Hub card.
- G4 Keep generation in a separate optional artifact, FORECAST-flagged, dual-use gated.
- G5 Keep weights, datasets, and Hub publish behind principle VIII operator gates.
- G6 Attach inference to analyze as an optional SHADOW block; omit on failure (II fail-open).
- G7 Base / uncensored trunk: no chat template, no refusal head on civilian attested slang.

## Non-goals

- N1 Chat model, 7B+ general LM, or “Hyperlex GPT.” Spark 200B ceiling does not change this.
- N2 Numeric Brier, forecast eligibility, or settle automation from model scores.
- N3 Claiming the `semantic` route on open analysis (Spec 005).
- N4 Generating restricted wraps, jailbreak recipes, ASR boards, or reconstructable restricted payloads.
- N5 Importing Abraxas or writing rune registry / Forecast spines (V).
- N6 Rewriting historical receipt hashes (VI).
- N7 Opening Spec 006 IsA.
- N8 Promoting `scripts/shadow/hyperlexical/` into `src/hyperlex/` without T13.
- N9 Training on live restricted-intent corpora.
- N10 Auto-registering cron, Chroma promote, or Hub upload.
- N11 Using a safety-tuned instruct checkpoint as the T1 product trunk.
- N12 Calling “uncensored” a reason to emit wraps.

## Users

- Hyperlex operator (primary) — wants a checkable encoder that improves lineage re-rank and unbind, trained on the Spark.
- Reviewer — needs dual-use answers and eval gates before any Hub card.
- Hermes host — may call a local inference helper; treats JSON as untrusted (LLM10).

## In scope (v0.1 specify)

- Packet schema and epistemic rules.
- Architecture contract: encoder + heads; optional separate generative LoRA later.
- Role schemes inherited from 004: `positional`, `type_slot` only.
- Dataset contract: gold from receipts/fixtures; weak labels marked INFERRED.
- Eval gates: lineage F1, unbind accuracy vs 004 probe, retrieval recall@k, dual-use fixture wall, no-refusal on civilian slang (E6).
- SHADOW CLI sketch: `hyperlexical-infer` under `scripts/shadow/hyperlexical/`.
- Hugging Face publish rules (operator-gated, sanitized card).
- Spark hardware contract and uncensored contract.

## Out of scope (v0.1)

- Training run, weight files in this repo, Hub upload.
- Decoder / mutation generation card.
- ANN backend (Roadmap 5.3 still deferred).
- API_V1 / API_EXTENDED symbols.
- 006 IsA taxonomy.
- Changing 004 probe code.
- Full-parameter 70B SFT just because Spark can hold it.

## Architecture (normative)

### Tiers

| Tier | Artifact | Params | Ships when | Name allowed |
|------|----------|--------|------------|--------------|
| T0 | Frozen public **base** encoder + linear heads | 22–40M | after dataset freeze + classify eval | `hyperlex-encoder-33m` |
| T1 | Encoder + multi-task + unbind heads | 60–150M | after unbind gate vs 004 probe | `hyperlex-structure-149m` (ModernBERT-base class) or `hyperlex-structure-110m` |
| T2 | Separate decoder LoRA | 151–360M adapter | only if operator says generate | `hyperlex-mutate-135m-lora` |
| T3 | From-scratch lexical toy | ≤30M | research only | not Hyperlexical |

T1 is the first artifact that may be called Hyperlexical. T0 is a baseline encoder. T2 is not this spec’s implement target.

Teacher models hosted on Spark (any size that fits 128 GB, including ModernBERT-large) are not the product card.

### Heads (T0/T1)

- lineage: closed set = 8 families + `ytd_leaf` + `none`
- typology: multi-label from existing SIGNAL REPORT roles (tribal, compression, irony_shield, status, hook, ritual, camouflage)
- stage: ordinal `{noise, circulating, contested, hyperstition_ish}` — INFERRED, not Brier
- mutation_type: optional detect-only tags aligned to 001/003 enums present on the span
- role / filler projectors for `type_slot` and `positional` unbind
- **no refusal head**

### Losses (T1)

- classification CE / BCE
- contrastive pull on same-family gold pairs
- unbind reconstruction: recover role and filler from the bound vector better than Spec 004 linear probe on the same fixtures

### Runtime constraints

- Train home: DGX Spark. See `hardware.md`.
- Offline inference required for unit tests and `HYPERLEX_OFFLINE=1`.
- No network to download weights during pytest; fixtures use stub vectors.
- Fail-open: if weights missing, omit `analysis.hyperlexical` and continue analyze.
- `provenance.brier` remains null on the packet and on any analyze attachment.
- Infer path has no chat template and no assistant string.
- aarch64 packaging for Spark; x86 CI may stub.
- NVFP4 export optional. Not an E2 gate.

### Uncensored constraints

See `uncensored.md`. Short form:

- Base trunk. Civilian slang including dialect / vulgar / sacred atoms must yield a packet.
- Restricted-intent spans still drop `surface` and keep `payload_ref`.
- No wrap generation.

## Packet (normative)

Schema id: `hyperlex.hyperlexical.inference.v0.1`  
File: `schemas/hyperlexical_inference.v0.1.schema.json`

Hard constants:

- `brier` = null
- `forecast_eligible` = false
- `routes_claimed` ⊆ `{form, lexical}` — never `semantic`
- `class` for lineage/typology/stage = `INFERRED` unless the label is copied from an operator-settled gold row (`OBSERVED` copy only)
- `unbind` class = `INFERRED`
- `model_id` required when weights ran; `stub` allowed in tests
- `param_count` integer or null
- if `restricted_intent_suspected`: drop `surface`; keep `payload_ref` hash only
- forbidden keys: `symbolic`, `has_symbols`

Analyze attachment (optional):

```json
"analysis": {
  "hyperlexical": {
    "schema": "hyperlex.hyperlexical.inference.v0.1",
    "model_id": "stub",
    "lineage_family": "none",
    "lineage_confidence": 0.0,
    "unbind_ok": false,
    "routes_claimed": ["lexical"],
    "brier": null,
    "forecast_eligible": false,
    "class": "INFERRED"
  }
}
```

Omit the block when the helper is absent or returns empty.

## Dataset contract (normative)

| Split | Source | Label class | Notes |
|-------|--------|-------------|-------|
| gold | `examples/` fixtures, golden receipts, 004 unbind pairs, settled rows | OBSERVED labels | lexical split; no lemma leak into test |
| weak | live-route harvest labeled by current detectors | INFERRED | never used as sole unbind gate |
| neg | ordinary prose, brands, names, AI-slop clichés | OBSERVED negative | required |
| dialect | civilian informal / vulgar / identity-routing atoms | OBSERVED | required for E6 |
| restricted | none in repo | n/a | flag-and-redact only if a span trips 001 C6 |

Minimum to *plan* implement: 200 gold classify rows + 40 unbind pairs + 50 negatives.  
Minimum to *name* a T1 card: 2k gold+weak classify + 200 unbind pairs + 200 negatives, lexical split.

## Eval gates (normative)

| Gate | Metric | Pass |
|------|--------|------|
| E0 smoke | schema valid; brier null; no semantic route | required for any merge of helper |
| E1 classify | macro-F1 lineage on lexical-split gold | beat current `match_lineage` on same split |
| E2 unbind | role+filler exact / slot accuracy | beat Spec 004 probe on shared fixtures |
| E3 retrieve | recall@5 vs `vector.db` seeds | ≥ baseline MiniLM if present, else documented |
| E4 dual-use | restricted fixtures persist no surface | wall test |
| E5 offline | tests pass under no-network | required |
| E6 no-refusal | dialect/informal civilian fixtures yield a packet, never a chat refusal string | required |

If E2 fails, the Hub card MUST NOT use the word Hyperlexical. Publish as encoder baseline or do not publish.

## Hugging Face rules (normative)

- Operator gate before any `huggingface-cli upload` or model card publish (VIII).
- Card states: SHADOW, not a receipt, Brier null until human settle, detect-over-generate, no chat template, base/uncensored encoder, trained on Spark.
- Sanitized dataset subset only. No raw ledger, no restricted spans.
- Weights are not the system of record. Local `~/.hyperlex/` remains source of truth.

## Functional requirements

- F1 Packet schema in repo; invalid packets fail tests.
- F2 SHADOW helper lives under `scripts/shadow/hyperlexical/`; no `src/hyperlex` import of torch in v0.1 specify cycle.
- F3 Helper may return a stub packet in CI without weights.
- F4 Analyze attachment is optional and fail-open.
- F5 No API_V1 change.
- F6 No Abraxas import.
- F7 No Brier number anywhere in the packet.
- F8 No `semantic` in `routes_claimed`.
- F9 Dual-use wall matches 001/003: no wrap verb, no generate path in this spec.
- F10 Docs point at this spec + Notion operator pages.
- F11 No chat template in infer.
- F12 Spark is train home; CI does not require a Spark.

## Success

Specify pack in repo. Notion operator pages exist. Clarifications C1–C52 recorded. U1–U3 harness on main. Training on Spark and Hub publish stay later cycles.

## References

- Hyperlex constitution v1.0.0
- Specs 000, 001, 003, 004, 005
- Spec 004 packet `abraxas.recoverable_structure.probe.v0.1` (unbind baseline, not a dependency import)
- Smolensky TPR (role–filler) as the 004 probe’s conceptual source — citation only
- NVIDIA DGX Spark / GB10 datasheet — 128 GB unified, aarch64, `sm_121`
- Warner et al. ModernBERT (arXiv:2412.13663) — citation only; T1-legal after A1
- OWASP GenAI LLM Top 10 2026 LLM01 / LLM03 / LLM10
