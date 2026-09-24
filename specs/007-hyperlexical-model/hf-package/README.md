---
license: apache-2.0
library_name: transformers
pipeline_tag: text-classification
base_model: answerdotai/ModernBERT-base
base_model_relation: adapter
tags:
  - encoder
  - slang
  - hyperlex
  - not-chat
---

# hyperlex-encoder-modernbert-base-seed

**Do not treat this as a publicly named Hyperlexical artifact yet.** Trained trunk-forward E2 has **PASSED**, but `name_gate=false` remains the explicit public-name/publish wall. This card is the publish *shape*. Weights are produced on Spark and are not in git.

## Current pin

- BEST: `seed-morph78`
- Promotion: `PROMOTE_BEST` via soft_ceiling ceiling escape on 2026-09-24
- Broad OBSERVED: **0.9883**, n=256
- PRIOR: morph65 **0.8867**, n=256
- E2: **PASS**
- Force/hard: **236 / 277**
- Upsample freeze: **11+**
- `SECOND_SLOT=4`: forbidden
- `name_gate`: **false**
- Brier: **null**
- Hub: unpublished

## Model details

- Trunk: [`answerdotai/ModernBERT-base`](https://huggingface.co/answerdotai/ModernBERT-base) (~149M, Apache-2.0)
- Adapter: classify `Linear(768, 9)` + unbind role/filler heads on last-layer token states
- Freeze: last 2 encoder layers trainable
- Tokenizer: official ModernBERT BPE (`local_files_only`)
- Train box: NVIDIA DGX Spark (GB10), aarch64, `sm_121`
- Packet: `hyperlex.hyperlexical.inference.v0.1`
- Brier: always null. Not a forecast.

Load the trunk from a local snapshot. Load heads from the pinned Spark artifact. There is no chat template.

## Intended use

Offline civilian slang lineage detect and structure-unbind. Library helper.

## Out of scope

Chat. Jailbreak / wrap generation. Semantic-route claims. Spec 006 is-a. Tool fire. Hugging Face text-generation pipeline.

## Alignment

Uncensored in the Hyperlex sense: no refusal head on civilian dialect. Dual-use wall remains. Restricted spans persist as `payload_ref` only.

## Training data

Git-tracked seed `civilian.v0.1.jsonl` is an 883-row snapshot and is **not** the train SoT. T1 training uses the local store / `--include-live` under operator settlement rules. INFERRED typology/stage does not become gold merely by inclusion.

## Eval

| Gate | Status | Note |
|------|--------|------|
| E0 packet | PASS | packet/schema path |
| E1 classify vs fixture | PARTIAL / receipt-bound | do not infer beyond receipts |
| E2 unbind vs Spec 004 probe | **PASS** | trained trunk-forward on pinned model |
| E3 MiniLM control | NOT_COMPUTABLE here | no current evidence added by this reconciliation |
| E4 restricted surface drop | PASS | existing governed surface |
| E5 schema / walls | PASS | no semantic/symbolic authority mint |
| E6 dialect no refusal | PASS | existing governed surface |

This reconciliation updates stale pre-train wording only. It does not manufacture new eval evidence.

## Naming / publication gate

E2 PASS does **not** flip the product name. Public `Hyperlexical` naming, Hub upload, and optional T13 promotion remain separate operator actions. Until explicit `name_gate` authorization, retain `hyperlex-encoder-*` naming and keep weights off git.

## Limitations

Small/curated slang surface; US-internet-heavy distribution; registry families are project taxonomies, not demographic labels; no general NLU claim; no forecast authority.

## Citation / contact

Operator gate. This file is not a Hub upload.
