"""Search helpers over the vector DB (supports sqlite and chroma backends)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .embed import embed_text
from .store import default_vector_db_path
from .chroma import get_vector_store


def vector_search(
    query: str,
    *,
    path: Optional[Path | str] = None,
    kind: Optional[str] = None,
    family_id: Optional[str] = None,
    top_k: int = 10,
    min_score: float = 0.15,
    backend: Optional[str] = None,
) -> Dict[str, Any]:
    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "empty query", "hits": []}
    vec, info = embed_text(q)

    backend = backend or __import__("os").environ.get("HYPERLEX_VECTOR_BACKEND", "sqlite")

    if backend == "chroma":
        store = get_vector_store(backend="chroma")
        hits = store.search(
            vec,
            kind=kind,
            family_id=family_id,
            top_k=top_k,
            min_score=min_score,
            model=info.model_id if info.provider == "hash" else None,
        )
        if not hits and info.provider != "hash":
            hits = store.search(vec, kind=kind, family_id=family_id, top_k=top_k, min_score=min_score)
        stats = store.stats()
        db_ref = f"chroma:{getattr(store, 'collection_name', 'hyperlex')}"
    else:
        from .store import VectorStore
        with VectorStore(path) as store:
            hits = store.search(
                vec,
                kind=kind,
                family_id=family_id,
                top_k=top_k,
                min_score=min_score,
                model=info.model_id if info.provider == "hash" else None,
            )
            if not hits and info.provider != "hash":
                hits = store.search(vec, kind=kind, family_id=family_id, top_k=top_k, min_score=min_score)
            stats = store.stats()
        db_ref = str(Path(path) if path else default_vector_db_path())

    return {
        "schema": "hyperlex.vector_search.v1",
        "ok": True,
        "query": q,
        "model": info.model_id,
        "embed_provenance": info.provenance,
        "top_k": top_k,
        "min_score": min_score,
        "n_hits": len(hits),
        "hits": hits,
        "db_path": db_ref,
        "db_n_total": stats.get("n_total"),
        "brier": None,
        "note": "Similarity is cosine over unit vectors; not a calibrated probability / Brier.",
        "backend": backend,
    }


def search_similar_terms(query: str, **kwargs: Any) -> Dict[str, Any]:
    return vector_search(query, kind="term", **kwargs)


def search_similar_receipts(query: str, **kwargs: Any) -> Dict[str, Any]:
    return vector_search(query, kind="receipt", **kwargs)
