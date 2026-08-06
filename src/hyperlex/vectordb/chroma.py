"""ChromaDB backend for Hyperlex vector store.

Modes (first match wins):
  1. Explicit client= passed to ChromaVectorStore / get_vector_store
  2. Local PersistentClient when path= or HYPERLEX_CHROMA_PATH is set
  3. CloudClient when cloud credentials are set

Usage (cloud)::

    export HYPERLEX_CHROMA_API_KEY=...
    export HYPERLEX_CHROMA_TENANT=...
    export HYPERLEX_CHROMA_DATABASE=Demo
    export HYPERLEX_VECTOR_BACKEND=chroma

Usage (local persistent)::

    export HYPERLEX_VECTOR_BACKEND=chroma
    export HYPERLEX_CHROMA_PATH=~/.hyperlex/chroma

Then vector-search / vector-seed use Chroma (or pass backend=\"chroma\").
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import chromadb
    from chromadb import CloudClient
except ImportError:  # pragma: no cover
    chromadb = None
    CloudClient = None


DEFAULT_COLLECTION = os.environ.get("HYPERLEX_CHROMA_COLLECTION", "hyperlex")


def _cloud_credentials() -> tuple[Optional[str], Optional[str], Optional[str]]:
    return (
        os.environ.get("HYPERLEX_CHROMA_API_KEY"),
        os.environ.get("HYPERLEX_CHROMA_TENANT"),
        os.environ.get("HYPERLEX_CHROMA_DATABASE"),
    )


def resolve_chroma_path(path: Optional[Path | str] = None) -> Optional[Path]:
    """Return a local chroma persist path if configured, else None."""
    raw = path if path is not None else os.environ.get("HYPERLEX_CHROMA_PATH")
    if raw is None or str(raw).strip() == "":
        return None
    return Path(str(raw)).expanduser()


def get_chroma_client(path: Optional[Path | str] = None) -> Any:
    """Create a Chroma client (local PersistentClient or CloudClient).

    Local path (preferred when set):
      path= argument, or HYPERLEX_CHROMA_PATH

    Cloud credentials (when no local path):
      HYPERLEX_CHROMA_API_KEY
      HYPERLEX_CHROMA_TENANT
      HYPERLEX_CHROMA_DATABASE

    Optional:
      HYPERLEX_CHROMA_COLLECTION (default: \"hyperlex\")
    """
    if chromadb is None:
        raise RuntimeError("chromadb is not installed. pip install 'hyperlex[runtime]' or chromadb")

    local_path = resolve_chroma_path(path)
    if local_path is not None:
        local_path.mkdir(parents=True, exist_ok=True)
        return chromadb.PersistentClient(path=str(local_path))

    if CloudClient is None:
        raise RuntimeError("chromadb is not installed. pip install chromadb")

    api_key, tenant, database = _cloud_credentials()
    if not api_key or not tenant or not database:
        raise RuntimeError(
            "Chroma not configured. Set a local path or cloud credentials:\n"
            "  Local:  HYPERLEX_CHROMA_PATH=~/.hyperlex/chroma\n"
            "  Cloud:  HYPERLEX_CHROMA_API_KEY / HYPERLEX_CHROMA_TENANT / HYPERLEX_CHROMA_DATABASE"
        )

    return CloudClient(api_key=api_key, tenant=tenant, database=database)


def _sanitize_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Chroma metadata values must be str/int/float/bool; drop None."""
    out: Dict[str, Any] = {}
    for k, v in meta.items():
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            out[str(k)] = v
        else:
            out[str(k)] = str(v)
    return out


class ChromaVectorStore:
    """ChromaDB-backed vector store with the same interface as the SQLite VectorStore."""

    def __init__(
        self,
        client: Optional[Any] = None,
        collection_name: str = DEFAULT_COLLECTION,
        path: Optional[Path | str] = None,
        **_ignored: Any,
    ):
        if chromadb is None:
            raise RuntimeError("chromadb package is required for ChromaVectorStore")

        self.path = resolve_chroma_path(path)
        self.client = client or get_chroma_client(path=self.path)
        self.collection_name = collection_name or DEFAULT_COLLECTION
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
        m = _sanitize_meta(dict(meta or {}))
        m.update(_sanitize_meta({
            "kind": kind,
            "text": text,
            "model": model,
            "family_id": family_id,
        }))
        # Chroma expects list of lists for embeddings
        self.collection.upsert(
            ids=[id],
            embeddings=[list(embedding)],
            documents=[text],
            metadatas=[m],
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
            embeddings.append(list(r["embedding"]))
            documents.append(r["text"])
            m = _sanitize_meta(dict(r.get("meta") or {}))
            m.update(_sanitize_meta({
                "kind": r.get("kind"),
                "text": r.get("text"),
                "model": r.get("model"),
                "family_id": r.get("family_id"),
            }))
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
        # Chroma requires a single top-level operator when combining filters.
        clauses: List[Dict[str, Any]] = []
        if kind:
            clauses.append({"kind": kind})
        if family_id:
            clauses.append({"family_id": family_id})
        if model:
            clauses.append({"model": model})
        if not clauses:
            where: Optional[Dict[str, Any]] = None
        elif len(clauses) == 1:
            where = clauses[0]
        else:
            where = {"$and": clauses}

        results = self.collection.query(
            query_embeddings=[list(embedding)],
            n_results=max(1, int(top_k)),
            where=where,
            include=["documents", "metadatas", "distances"],
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

    def count(self, kind: Optional[str] = None) -> int:
        """Match SQLite VectorStore.count signature (kind filter is best-effort)."""
        try:
            if kind:
                # Chroma has no cheap filtered count; use get with where when available
                try:
                    got = self.collection.get(where={"kind": kind}, include=[])
                    return len(got.get("ids") or [])
                except Exception:
                    return self.collection.count()
            return self.collection.count()
        except Exception:
            return 0

    def stats(self) -> Dict[str, Any]:
        n = self.count()
        out: Dict[str, Any] = {
            "schema": "hyperlex.vector_stats.v1",
            "backend": "chroma",
            "collection": self.collection_name,
            "n_total": n,
        }
        if self.path is not None:
            out["path"] = str(self.path)
        else:
            out["path"] = f"chroma-cloud:{self.collection_name}"
        return out

    def close(self) -> None:
        # Persistent/Cloud clients do not require explicit close
        pass


def get_vector_store(backend: Optional[str] = None, **kwargs: Any):
    """Factory that returns the appropriate vector store.

    backend: \"sqlite\" (default) or \"chroma\"

    For chroma, ``path`` maps to a local PersistentClient directory
    (or falls through to cloud credentials when unset).
    """
    backend = (backend or os.environ.get("HYPERLEX_VECTOR_BACKEND", "sqlite")).lower()

    if backend == "chroma":
        # Accept path= from seed_all / CLI without TypeError
        return ChromaVectorStore(
            client=kwargs.get("client"),
            collection_name=kwargs.get("collection_name", DEFAULT_COLLECTION),
            path=kwargs.get("path"),
        )

    # fallback to sqlite
    from .store import VectorStore

    return VectorStore(**kwargs)
