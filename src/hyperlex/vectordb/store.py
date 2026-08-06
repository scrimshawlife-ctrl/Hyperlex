"""SQLite-backed local vector store."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .embed import cosine, pack_embedding, unpack_embedding


def default_vector_db_path() -> Path:
    import os

    env = os.environ.get("HYPERLEX_VECTOR_DB", "").strip()
    if env:
        return Path(env).expanduser()
    return Path.home() / ".hyperlex" / "vector.db"


class VectorStore:
    """Append/upsert vectors; linear scan search (fine for 10k-scale slang corpora)."""

    def __init__(self, path: Optional[Path | str] = None):
        self.path = Path(path) if path else default_vector_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS vectors (
              id TEXT PRIMARY KEY,
              kind TEXT NOT NULL,
              text TEXT NOT NULL,
              family_id TEXT,
              meta_json TEXT,
              dim INTEGER NOT NULL,
              embedding BLOB NOT NULL,
              model TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_vectors_kind ON vectors(kind);
            CREATE INDEX IF NOT EXISTS idx_vectors_family ON vectors(family_id);
            CREATE INDEX IF NOT EXISTS idx_vectors_model ON vectors(model);

            CREATE TABLE IF NOT EXISTS meta (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "VectorStore":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def upsert(
        self,
        *,
        id: str,
        kind: str,
        text: str,
        embedding: Sequence[float],
        model: str,
        family_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        blob = pack_embedding(embedding)
        self._conn.execute(
            """
            INSERT INTO vectors (id, kind, text, family_id, meta_json, dim, embedding, model, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              kind=excluded.kind,
              text=excluded.text,
              family_id=excluded.family_id,
              meta_json=excluded.meta_json,
              dim=excluded.dim,
              embedding=excluded.embedding,
              model=excluded.model,
              created_at=excluded.created_at
            """,
            (
                id,
                kind,
                text,
                family_id,
                json.dumps(meta or {}, sort_keys=True),
                len(embedding),
                blob,
                model,
                now,
            ),
        )
        self._conn.commit()

    def upsert_many(self, rows: Iterable[Dict[str, Any]]) -> int:
        n = 0
        for row in rows:
            self.upsert(
                id=str(row["id"]),
                kind=str(row["kind"]),
                text=str(row["text"]),
                embedding=row["embedding"],
                model=str(row["model"]),
                family_id=row.get("family_id"),
                meta=row.get("meta"),
            )
            n += 1
        return n

    def count(self, kind: Optional[str] = None) -> int:
        if kind:
            cur = self._conn.execute("SELECT COUNT(*) AS c FROM vectors WHERE kind=?", (kind,))
        else:
            cur = self._conn.execute("SELECT COUNT(*) AS c FROM vectors")
        return int(cur.fetchone()["c"])

    def stats(self) -> Dict[str, Any]:
        by_kind: Dict[str, int] = {}
        for row in self._conn.execute("SELECT kind, COUNT(*) AS c FROM vectors GROUP BY kind"):
            by_kind[str(row["kind"])] = int(row["c"])
        by_family: Dict[str, int] = {}
        for row in self._conn.execute(
            "SELECT COALESCE(family_id, '(none)') AS f, COUNT(*) AS c FROM vectors GROUP BY f ORDER BY c DESC LIMIT 40"
        ):
            by_family[str(row["f"])] = int(row["c"])
        models = [str(r["model"]) for r in self._conn.execute("SELECT DISTINCT model FROM vectors")]
        return {
            "schema": "hyperlex.vector_stats.v1",
            "path": str(self.path),
            "n_total": self.count(),
            "by_kind": by_kind,
            "by_family": by_family,
            "models": models,
        }

    def search(
        self,
        query_vec: Sequence[float],
        *,
        kind: Optional[str] = None,
        family_id: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.0,
        model: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        clauses = ["dim = ?"]
        params: List[Any] = [len(query_vec)]
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        if family_id:
            clauses.append("family_id = ?")
            params.append(family_id)
        if model:
            clauses.append("model = ?")
            params.append(model)
        sql = f"SELECT id, kind, text, family_id, meta_json, dim, embedding, model, created_at FROM vectors WHERE {' AND '.join(clauses)}"
        hits: List[Dict[str, Any]] = []
        for row in self._conn.execute(sql, params):
            vec = unpack_embedding(row["embedding"], dim=int(row["dim"]))
            score = cosine(query_vec, vec)
            if score < min_score:
                continue
            meta = {}
            try:
                meta = json.loads(row["meta_json"] or "{}")
            except json.JSONDecodeError:
                meta = {}
            hits.append({
                "id": row["id"],
                "kind": row["kind"],
                "text": row["text"],
                "family_id": row["family_id"],
                "meta": meta,
                "model": row["model"],
                "score": round(float(score), 6),
                "created_at": row["created_at"],
            })
        hits.sort(key=lambda h: h["score"], reverse=True)
        return hits[: max(1, int(top_k))]

    def delete_kind(self, kind: str) -> int:
        cur = self._conn.execute("DELETE FROM vectors WHERE kind=?", (kind,))
        self._conn.commit()
        return int(cur.rowcount or 0)

    def iter_rows(self, *, kind: Optional[str] = None) -> Iterable[Dict[str, Any]]:
        """Yield full vector rows (including embedding list) for export/sync."""
        if kind:
            cur = self._conn.execute(
                "SELECT id, kind, text, family_id, meta_json, dim, embedding, model, created_at "
                "FROM vectors WHERE kind=? ORDER BY id",
                (kind,),
            )
        else:
            cur = self._conn.execute(
                "SELECT id, kind, text, family_id, meta_json, dim, embedding, model, created_at "
                "FROM vectors ORDER BY id"
            )
        for row in cur:
            meta: Dict[str, Any] = {}
            try:
                meta = json.loads(row["meta_json"] or "{}")
            except json.JSONDecodeError:
                meta = {}
            yield {
                "id": str(row["id"]),
                "kind": str(row["kind"]),
                "text": str(row["text"]),
                "family_id": row["family_id"],
                "model": str(row["model"]),
                "embedding": unpack_embedding(row["embedding"], dim=int(row["dim"])),
                "meta": meta,
                "created_at": row["created_at"],
            }
