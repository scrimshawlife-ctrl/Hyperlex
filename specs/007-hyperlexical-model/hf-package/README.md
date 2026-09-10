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

**Do not treat this as Hyperlexical.** E2 has not passed. Name-gate is false. This card is the publish *shape*. Weights are produced on Spark and are not in git.

## Model details

- Trunk: [`answerdotai/ModernBERT-base`](https://huggingface.co/answerdotai/ModernBERT-base) (~149M, Apache-2.0)
- Adapter: classify `Linear(768, 9)` + unbind role/filler heads on last-layer token states
- Freeze: last 2 encoder layers trainable
- Tokenizer: official ModernBERT BPE (`local_files_only`)
- Train box: NVIDIA DGX Spark (GB10), aarch64, `sm_121`
- Packet: `hyperlex.hyperlexical.inference.v0.1`
- Brier: always null. Not a forecast.

Load the trunk from a local snapshot. Load heads from this directory (`model.safetensors` or `heads.pt`). There is no chat template.

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

Seed export `civilian.v0.1.jsonl` from Hyperlex fixtures, dialect atoms, registry (INFERRED), golden (INFERRED), archive (INFERRED). Lexical split. Name-gate counts are **not** met.

Do not treat INFERRED typology/stage as gold.

## Eval (pre-train / stub)

| Gate | Status | Note |
|------|--------|------|
| E0 packet on `rizz` | PASS | stub infer, brier null |
| E1 classify vs fixture | NOT RUN | needs Spark weights |
| E2 unbind vs Spec 004 probe | FAIL | stub swap < probe swap. Required for the word Hyperlexical |
| E3 MiniLM control | NOT RUN | control only, not the card |
| E4 restricted surface drop | PASS | `__RESTRICTED_FIXTURE__` |
| E5 schema / walls | PASS | no semantic, no symbolic |
| E6 dialect no refusal | PASS | `no cap fr` |

After Spark `--run`, replace this table with `train-receipt.json` val metrics and a new `eval_unbind` JSON. Do not flip E2 by editing the card.

## Limitations

Small seed. Crude first-occurrence aligner if offset mapping is missing. Last-2 freeze not ablated. Encoded slang is US-internet heavy. Not a general NLU encoder.

## Bias

Lineage families are Hyperlex registry families. They are not demographic labels. Registry rows are INFERRED.

## Citation / contact

Operator gate. This file is not a Hub upload.
