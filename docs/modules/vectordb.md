# Vector DB (local)

**Status:** v0.3.5  
**Path:** `~/.hyperlex/vector.db` (override: `HYPERLEX_VECTOR_DB`)  
**Backend:** SQLite + float32 embedding blobs (stdlib only)

Hyperlex keeps a **local vector database** for semantic search over:

- lineage registry terms  
- YTD backfill pack terms  
- receipt text (query + observed preview + matched terms)

This is the seedable “vector DB” alongside the receipt ledger. It is **not** a remote SaaS DB and does **not** invent Brier scores.

## Embeddings

| Provider | When | Notes |
|----------|------|--------|
| **hash** (default) | always offline | Deterministic feature-hash n-grams (`hyperlex.hash_ngram_v1.d256`) |
| **openai_compatible** | opt-in | `HYPERLEX_EMBED_PROVIDER=openai_compatible` + base URL/key |

```bash
# Offline seed (default)
python3 scripts/hyperlex.py vector-seed --include-golden --through 2026-08

# Stats
python3 scripts/hyperlex.py vector-stats

# Search
python3 scripts/hyperlex.py vector-search "sigma rizz locked in" --kind term --top-k 8
python3 scripts/hyperlex.py vector-search "agentic slop" --kind receipt
```

### Env

| Variable | Meaning |
|----------|---------|
| `HYPERLEX_VECTOR_DB` | Path to sqlite file |
| `HYPERLEX_EMBED_PROVIDER` | `hash` (default) or `openai_compatible` |
| `HYPERLEX_EMBED_BASE_URL` / `HYPERLEX_LLM_BASE_URL` | Embeddings API base |
| `HYPERLEX_EMBED_API_KEY` / `OPENAI_API_KEY` | API key |
| `HYPERLEX_EMBED_MODEL` | Remote model id |
| `HYPERLEX_OFFLINE=1` | Blocks remote embeddings |

## Seed sources

```bash
vector-seed
  --no-registry      # skip LINEAGE_REGISTRY
  --no-backfill       # skip data/backfill packs
  --no-receipts       # skip receipt files
  --include-home      # ~/.hyperlex/receipts (default on)
  --include-golden    # examples/receipts/golden
  --receipt-dir DIR
  --through 2026-08
```

## Library

```python
from hyperlex import vector_seed_all, vector_search, VectorStore, default_vector_db_path

report = vector_seed_all(through="2026-08", include_home=True)
hits = vector_search("rizz aura", kind="term", top_k=5)
```

## Hybrid lineage re-rank (0.3.5)

When the vector DB is present (`HYPERLEX_VECTOR=auto|1`), `match_lineage` combines:

```text
hybrid_confidence = min(0.98, lexical_confidence + vector_boost)
```

- `vector_boost` is a **capped** family mass from term neighbors (max +0.12)
- Near-miss lexical candidates can be rescued if hybrid clears the threshold
- Result may include `lineage.hybrid` with boosts + flip diagnostics
- Still **INFERRED**, still **not Brier**

Disable: `HYPERLEX_VECTOR=0` or `match_lineage(..., use_vector=False)`.

## Hard rules

1. Similarity scores are **not** probabilities and **not** Brier.  
2. Hash embeddings are **INFERRED**; remote embeddings are **OBSERVED** (network).  
3. Vector DB never rewrites receipt integrity hashes.  
4. Linear cosine scan is intentional at current scale (terms + receipts).

## Hermes seed prompt (short)

```text
Hyperlex: seed vector DB. HYPERLEX_OFFLINE=1.
vector-seed --include-golden --through 2026-08
vector-stats
vector-search "sigma rizz locked in" --kind term
Report n_total, by_kind, sample hits. Never invent Brier.
```
