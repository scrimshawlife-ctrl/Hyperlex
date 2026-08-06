from .embed import embed_text, embed_batch, EmbeddingModelInfo, default_model_id
from .store import VectorStore, default_vector_db_path
from .seed import seed_from_backfill, seed_from_registry, seed_from_receipts, seed_all
from .search import vector_search, search_similar_terms, search_similar_receipts
from .chroma import ChromaVectorStore, get_chroma_client, get_vector_store
from .transfer import export_vectors, import_vectors, sync_vectors, open_vector_store
from .autoindex import (
    index_from_analysis,
    index_receipt_path,
    index_texts,
    vector_auto_enabled,
    vector_backend,
)

__all__ = [
    "embed_text",
    "embed_batch",
    "EmbeddingModelInfo",
    "default_model_id",
    "VectorStore",
    "default_vector_db_path",
    "ChromaVectorStore",
    "get_chroma_client",
    "get_vector_store",
    "seed_from_backfill",
    "seed_from_registry",
    "seed_from_receipts",
    "seed_all",
    "vector_search",
    "search_similar_terms",
    "search_similar_receipts",
    "export_vectors",
    "import_vectors",
    "sync_vectors",
    "open_vector_store",
    "index_from_analysis",
    "index_receipt_path",
    "index_texts",
    "vector_auto_enabled",
    "vector_backend",
]
