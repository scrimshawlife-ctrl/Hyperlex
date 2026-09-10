# Trunk freeze 007 — A2

**Frozen T1 trunk:** `answerdotai/ModernBERT-base`  
**Params:** ~149M  
**License:** Apache 2.0  
**Cite:** Warner et al. arXiv:2412.13663; HF `answerdotai/ModernBERT-base`  
**Operator path:** continue-as-recommended after A1 (2026-09-09)

## Frozen facts

| Field | Value |
|-------|-------|
| Architecture | Encoder-only ModernBERT |
| Layers / hidden / heads | 22 / 768 / 12 |
| Vocab | 50,368 BPE (modified OLMo) |
| Context trained | 8,192 |
| Context used in 007 | atom-length; 256 cap in v0.1 infer is enough |
| Positional | RoPE; local window 128; global every 3rd layer |
| Chat template | none |
| Refusal head | none |

## How 007 uses it

- **Unbind heads (E2)** read **last-layer token hidden states** (768-d per token). Not mean-pool. Not sentence-transformers wrap.
- **Retrieve head (E3)** may mean-pool or CLS-pool the same states. MiniLM remains the E3 *control*, not the trunk.
- **Classify heads (E1)** sit on pooled 768-d. Pooling method documented at train time.
- Tokenizer is the official ModernBERT tokenizer. Do not retokenize with BERT WordPiece.

## Not frozen by A2

- Head architecture details beyond “linear / small MLP on 768”
- Learning rates, batch, epochs
- Whether to freeze lower layers on Spark
- NVFP4 export
- Hub upload
- U1 stub still uses `STATIC_HASH_EMBEDDING` (no 149M download in CI)

## Replaces

`trunk-candidates.md` stays as history. This file is the freeze. U3 may not silently swap the trunk.
