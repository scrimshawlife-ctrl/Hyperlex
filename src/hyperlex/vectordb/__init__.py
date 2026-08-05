"""Local vector DB for Hyperlex (SQLite + deterministic embeddings).

Primary path: ``~/.hyperlex/vector.db``

Offline by default (hash-embedding). Optional remote embeddings via
``HYPERLEX_EMBED_PROVIDER=openai_compatible`` (same base URL style as LLM).

Never invents Brier. Never rewrites receipt integrity.
"""

from .embed import embed_text, embed_batch, EmbeddingModelInfo, default_model_id
from .store import VectorStore, default_vector_db_path
from .seed import seed_from_backfill, seed_from_registry, seed_from_receipts, seed_all
from .search import vector_search, search_similar_terms, search_similar_receipts

__all__ = [
    "embed_text",
    "embed_batch",
    "EmbeddingModelInfo",
    "default_model_id",
    "VectorStore",
    "default_vector_db_path",
    "seed_from_backfill",
    "seed_from_registry",
    "seed_from_receipts",
    "seed_all",
    "vector_search",
    "search_similar_terms",
    "search_similar_receipts",
]
