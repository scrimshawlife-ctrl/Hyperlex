# Trunk candidates 007 — not frozen

U3 picks one. This file is a shortlist. C16 still holds: no Qwen dump as the product trunk.

All rows are **base encoders**. No instruct-chat. No safety-tuned chat template.

| Id | Params | Tier fit | Notes |
|----|--------|----------|-------|
| `sentence-transformers/all-MiniLM-L6-v2` | ~22M | T0 | Current Hyperlex-adjacent size. Public. Not a reasoner. |
| `BAAI/bge-small-en-v1.5` | ~33M | T0 | Stronger retrieval baseline for E3. |
| `jhu-clsp/ettin-encoder-32m` | ~32M | T0 | Modern encoder scale. |
| `jhu-clsp/ettin-encoder-68m` | ~68M | T1 low | Inside 60–130M. |
| `bert-base-uncased` | ~110M | T1 | Classic MLM. Wordpiece will mangle slang; still a legal trunk. |
| `answerdotai/ModernBERT-base` | ~149M | **over C6** | Teacher or C6 amendment only. |
| Hash stub `STATIC_HASH_EMBEDDING` | 0 | CI | Control only. Not Hyperlexical. |

## Rejected as T1 card

- Any `*-instruct` / chat / Llama / Qwen-chat checkpoint
- Safety-tuned embedding APIs that refuse dialect
- 7B+ decoders hosted on Spark “because they fit”
- U1b frozen Qwen dump (C16)

## Spark note

Every legal T1 trunk is a rounding error on 128 GB. Bandwidth, not capacity, is the constraint. Keep T1 small.
