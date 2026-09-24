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
- Train val (force surface): best unbind_exact **1.0** n=164 at epoch 15
- E2: **PASS** (trained trunk-forward, unbind_exact 1.0, n_unbind_eval 24)
- Force/hard: **236 / 277**
- This pin: observed upsample **10**, second-slot weight **2.0**, LAST_TRAINABLE **8**, 40 epochs, warm from morph65
- Upsample freeze: **11+** · `SECOND_SLOT=4`: forbidden
- `name_gate`: **false**
- Brier: **null**
- Hub: unpublished

## Model details

- Trunk: [`answerdotai/ModernBERT-base`](https://huggingface.co/answerdotai/ModernBERT-base) (~149M, Apache-2.0)
- Adapter: classify `Linear(768, 9)` + unbind role/filler heads on last-layer token states
- Freeze: last 8 encoder layers trainable on `seed-morph78` (recipe default for seed smoke is last 2)
- Tokenizer: official ModernBERT BPE (`local_files_only`)
- Train box: NVIDIA DGX Spark (GB10), aarch64, `sm_121`
- Packet: `hyperlex.hyperlexical.inference.v0.1`
- Brier: always null. Not a forecast.

Load the trunk from a local snapshot. Load heads from the pinned artifact directory (`model.safetensors`). Weights are on Spark only until a Hub upload is authorized. There is no chat template.

```python
from transformers import AutoModel, AutoTokenizer
tok = AutoTokenizer.from_pretrained(trunk_dir, local_files_only=True)
enc = AutoModel.from_pretrained(trunk_dir, local_files_only=True)
# heads: classify / role_head / filler_head in model.safetensors
```

## Intended use

Offline civilian slang lineage detect and structure-unbind. Library helper.

## Out of scope

Chat. Jailbreak / wrap generation. Semantic-route claims. Spec 006 is-a. Tool fire. Hugging Face text-generation pipeline.

## Alignment

Uncensored in the Hyperlex sense: no refusal head on civilian dialect. Dual-use wall remains. Restricted spans persist as `payload_ref` only.

## Training data

Git-tracked seed `civilian.v0.1.jsonl` is an 883-row snapshot and is **not** the train SoT. T1 training uses the local store / `--include-live` under operator settlement rules (`seed-morph78`: live rows included 4258, train classify 4062, train unbind 15536). INFERRED typology/stage does not become gold merely by inclusion.

## Eval

| Gate | Status | Note |
|------|--------|------|
| E0 packet on `rizz` | PASS (stub harness) | not re-run against `seed-morph78` weights |
| E1 classify vs fixture | NOT_COMPUTABLE | no E1 receipt for `seed-morph78`. Train-receipt val `classify_acc` 0.7733 n=516 is a train metric, not E1 |
| E2 unbind vs Spec 004 probe | **PASS** | `seed-morph78` trunk-forward: unbind_exact 1.0, token/slot F1 1.0, model_swap 1.0 ≥ probe_swap_min 0.5 |
| E3 MiniLM control | NOT_COMPUTABLE | control only; no receipt |
| E4 restricted surface drop | PASS (stub harness) | `__RESTRICTED_FIXTURE__`; not re-run against `seed-morph78` weights |
| E5 schema / walls | PASS (stub harness) | no semantic, no symbolic |
| E6 dialect no refusal | PASS (stub harness) | `no cap fr`; not re-run against `seed-morph78` weights |

E2 source: `receipts/morph78-val-settle-20260924/e2-unbind-morph78.json`. That directory's `train-receipt.json` carries `e2_pass: false` because train does not run E2. The separate E2 eval and `GATE_LOCK.json` record the pass. Do not flip any gate by editing this card.

## Naming / publication gate

E2 PASS does **not** flip the product name. Public `Hyperlexical` naming, Hub upload, and optional T13 promotion remain separate operator actions. Until explicit `name_gate` authorization, retain `hyperlex-encoder-*` naming and keep weights off git.

## Limitations

First-occurrence aligner fallback if offset mapping is missing (`seed-morph78` used `char_span + offset_mapping`). Small/curated slang surface; US-internet-heavy distribution; registry families are project taxonomies, not demographic labels; no general NLU claim; no forecast authority.

## Bias

Lineage families are Hyperlex registry families. They are not demographic labels. Registry rows are INFERRED.

## Citation / contact

Operator gate. This file is not a Hub upload.
