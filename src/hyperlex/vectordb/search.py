"""Search helpers over the local vector DB."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .embed import embed_text
from .store import VectorStore, default_vector_db_path


def vector_search(
    query: str,
    *,
    path: Optional[Path | str] = None,
    kind: Optional[str] = None,
    family_id: Optional[str] = None,
    top_k: int = 10,
    min_score: float = 0.15,
) -> Dict[str, Any]:
    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "empty query", "hits": []}
    vec, info = embed_text(q)
    with VectorStore(path) as store:
        hits = store.search(
            vec,
            kind=kind,
            family_id=family_id,
            top_k=top_k,
            min_score=min_score,
            model=info.model_id if info.provider == "hash" else None,
        )
        # if remote model id mismatch, fall back to search without model filter
        if not hits and info.provider != "hash":
            hits = store.search(vec, kind=kind, family_id=family_id, top_k=top_k, min_score=min_score)
        stats = store.stats()
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
        "db_path": str(Path(path) if path else default_vector_db_path()),
        "db_n_total": stats.get("n_total"),
        "brier": None,
        "note": "Similarity is cosine over unit vectors; not a calibrated probability / Brier.",
    }


def search_similar_terms(query: str, **kwargs: Any) -> Dict[str, Any]:
    return vector_search(query, kind="term", **kwargs)


def search_similar_receipts(query: str, **kwargs: Any) -> Dict[str, Any]:
    return vector_search(query, kind="receipt", **kwargs)
