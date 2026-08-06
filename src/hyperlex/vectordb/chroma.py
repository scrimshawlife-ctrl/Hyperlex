"""ChromaDB Cloud backend for Hyperlex vector store.

Usage:
    export HYPERLEX_CHROMA_API_KEY=...
    export HYPERLEX_CHROMA_TENANT=...
    export HYPERLEX_CHROMA_DATABASE=Demo
    export HYPERLEX_VECTOR_BACKEND=chroma

Then vector-search / vector-seed will use it (or pass backend="chroma").
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

try:
    import chromadb
    from chromadb import CloudClient
except ImportError:  # pragma: no cover
    chromadb = None
    CloudClient = None

from .embed import embed_text


DEFAULT_COLLECTION = os.environ.get("HYPERLEX_CHROMA_COLLECTION", "hyperlex")


def get_chroma_client() -> Any:
    """Create a Chroma CloudClient from environment variables.

    Required env vars:
      HYPERLEX_CHROMA_API_KEY
      HYPERLEX_CHROMA_TENANT
      HYPERLEX_CHROMA_DATABASE

    Optional:
      HYPERLEX_CHROMA_COLLECTION (default: "hyperlex")
    """
    if CloudClient is None:
        raise RuntimeError("chromadb is not installed. pip install chromadb")

    api_key = os.environ.get("HYPERLEX_CHROMA_API_KEY")
    tenant = os.environ.get("HYPERLEX_CHROMA_TENANT")
    database = os.environ.get("HYPERLEX_CHROMA_DATABASE")

    if not api_key or not tenant or not database:
        raise RuntimeError(
            "Chroma Cloud credentials not found. Set:\n"
            "  HYPERLEX_CHROMA_API_KEY\n"
            "  HYPERLEX_CHROMA_TENANT\n"
            "  HYPERLEX_CHROMA_DATABASE"
        )

    return CloudClient(api_key=api_key, tenant=tenant, database=database)


class ChromaVectorStore:
    """ChromaDB-backed vector store with the same interface as the SQLite VectorStore."""

    def __init__(
        self,
        client: Optional[Any] = None,
        collection_name: str = DEFAULT_COLLECTION,
    ):
        if chromadb is None:
            raise RuntimeError("chromadb package is required for ChromaVectorStore")

        self.client = client or get_chroma_client()
        self.collection_name = collection_name
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def upsert(
        self,
        id: str,
        kind: str,
        text: str,
        embedding: List[float],
        model: Optional[str] = None,
        family_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        meta = dict(meta or {})
        meta.update({
            "kind": kind,
            "text": text,
            "model": model,
            "family_id": family_id,
        })
        # Chroma expects list of lists for embeddings
        self.collection.upsert(
            ids=[id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[meta],
        )

    def upsert_many(self, rows: List[Dict[str, Any]]) -> int:
        if not rows:
            return 0
        ids = []
        embeddings = []
        documents = []
        metadatas = []
        for r in rows:
            ids.append(r["id"])
            embeddings.append(r["embedding"])
            documents.append(r["text"])
            m = dict(r.get("meta", {}))
            m.update({
                "kind": r.get("kind"),
                "text": r.get("text"),
                "model": r.get("model"),
                "family_id": r.get("family_id"),
            })
            metadatas.append(m)
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        return len(rows)

    def search(
        self,
        embedding: List[float],
        *,
        kind: Optional[str] = None,
        family_id: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.15,
        model: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        where: Dict[str, Any] = {}
        if kind:
            where["kind"] = kind
        if family_id:
            where["family_id"] = family_id
        if model:
            where["model"] = model

        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where if where else None,
            include=["embeddings", "documents", "metadatas", "distances"],
        )

        hits = []
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        for i, _id in enumerate(ids):
            dist = dists[i] if dists else 0.0
            # Chroma cosine distance: lower is better. Convert to similarity ~ 1 - dist
            score = max(0.0, 1.0 - float(dist))
            if score < min_score:
                continue
            m = metas[i] or {}
            hits.append({
                "id": _id,
                "kind": m.get("kind"),
                "text": docs[i] or m.get("text"),
                "score": round(score, 6),
                "family_id": m.get("family_id"),
                "model": m.get("model"),
                "meta": {k: v for k, v in m.items() if k not in ("kind", "text", "model", "family_id")},
            })

        # Sort by score desc (higher similarity first)
        hits.sort(key=lambda x: x["score"], reverse=True)
        return hits[:top_k]

    def count(self) -> int:
        try:
            return self.collection.count()
        except Exception:
            return 0

    def stats(self) -> Dict[str, Any]:
        n = self.count()
        # Chroma doesn't give easy per-kind counts without extra queries
        return {
            "backend": "chroma",
            "collection": self.collection_name,
            "n_total": n,
        }

    def close(self) -> None:
        # Cloud client does not require explicit close
        pass


def get_vector_store(backend: Optional[str] = None, **kwargs: Any):
    """Factory that returns the appropriate vector store.

    backend: "sqlite" (default) or "chroma"
    """
    backend = backend or os.environ.get("HYPERLEX_VECTOR_BACKEND", "sqlite").lower()

    if backend == "chroma":
        return ChromaVectorStore(**kwargs)

    # fallback to sqlite
    from .store import VectorStore
    return VectorStore(**kwargs)