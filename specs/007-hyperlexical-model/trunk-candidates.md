# Trunk candidates 007 — not frozen

U3 picks one. C16 still holds: no Qwen dump as the product trunk.
C6 A1 (2026-09-09): T1 ≤ 150M. ModernBERT-base is now a legal T1 trunk.

All rows are **base encoders**. No instruct-chat. No safety-tuned chat template.

| Id | Params | Tier fit | Notes |
|----|--------|----------|-------|
| `sentence-transformers/all-MiniLM-L6-v2` | ~22M | T0 | Control / E3. WordPiece uncased mangles slang. |
| `BAAI/bge-small-en-v1.5` | ~33M | T0 | Stronger retrieval baseline for E3. |
| `jhu-clsp/ettin-encoder-32m` | ~32M | T0 | ModernBERT-style small. |
| `jhu-clsp/ettin-encoder-68m` | ~68M | T1 low | Inside ceiling. |
| `bert-base-uncased` | ~110M | T1 | Classic MLM. WordPiece still mangles slang. |
| `answerdotai/ModernBERT-base` | ~149M | **T1** (A1) | Preferred unbind trunk. OLMo BPE 50k. Not frozen until U3. |
| `answerdotai/ModernBERT-large` | ~395M | teacher only | Over C6. Spark-legal teacher. Not the card. |
| Hash stub `STATIC_HASH_EMBEDDING` | 0 | CI | Control only. Not Hyperlexical. |

## Rejected as T1 card

- Any `*-instruct` / chat / Llama / Qwen-chat checkpoint
- Safety-tuned embedding APIs that refuse dialect
- 7B+ decoders hosted on Spark “because they fit”
- U1b frozen Qwen dump (C16)
- ModernBERT-large as the named card

## Spark note

149M is still a rounding error on 128 GB. Bandwidth, not capacity, is the constraint.
