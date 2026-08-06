"""Export / import / sync vector rows between sqlite, local Chroma, and Chroma Cloud.

Recommended promote path::

    # 1. Build locally
    hyperlex vector-seed --backend chroma --db ~/.hyperlex/chroma --no-receipts

    # 2a. One-shot when cloud creds are set (preferred)
    hyperlex vector-sync --from-path ~/.hyperlex/chroma --to cloud

    # 2b. Or staged jsonl
    hyperlex vector-export --backend chroma --db ~/.hyperlex/chroma -o good.jsonl
    hyperlex vector-import -i good.jsonl --backend chroma --cloud
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .chroma import ChromaVectorStore, DEFAULT_COLLECTION
from .store import VectorStore

ROW_SCHEMA = "hyperlex.vector_row.v1"
EXPORT_SCHEMA = "hyperlex.vector_export.v1"
SYNC_SCHEMA = "hyperlex.vector_sync.v1"
IMPORT_SCHEMA = "hyperlex.vector_import.v1"

UPSERT_BATCH = 128


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_row(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a dict (from store.iter_rows or jsonl) into upsert-ready shape."""
    emb = raw.get("embedding")
    if emb is None:
        raise ValueError(f"row {raw.get('id')!r} missing embedding")
    embedding = [float(x) for x in emb]
    if not embedding:
        raise ValueError(f"row {raw.get('id')!r} has empty embedding")
    meta = dict(raw.get("meta") or {})
    # allow full chroma-style flat meta on the wire
    for k in ("kind", "text", "model", "family_id"):
        meta.pop(k, None)
    return {
        "id": str(raw["id"]),
        "kind": str(raw.get("kind") or "term"),
        "text": str(raw.get("text") or ""),
        "family_id": raw.get("family_id"),
        "model": str(raw.get("model") or ""),
        "embedding": embedding,
        "meta": meta,
    }


def open_vector_store(
    *,
    backend: str = "sqlite",
    path: Optional[Path | str] = None,
    force_cloud: bool = False,
    collection_name: Optional[str] = None,
    client: Any = None,
) -> Any:
    """Open a store for transfer.

    backend: sqlite | chroma
    force_cloud: target Chroma Cloud (ignores HYPERLEX_CHROMA_PATH)
    """
    backend = (backend or "sqlite").strip().lower()
    if backend == "chroma":
        return ChromaVectorStore(
            client=client,
            path=None if force_cloud else path,
            collection_name=collection_name or DEFAULT_COLLECTION,
            force_cloud=force_cloud,
        )
    if force_cloud:
        raise ValueError("force_cloud only applies to backend=chroma")
    return VectorStore(path=path)


def export_vectors(
    *,
    out_path: Path | str,
    backend: str = "sqlite",
    path: Optional[Path | str] = None,
    kind: Optional[str] = None,
    force_cloud: bool = False,
    collection_name: Optional[str] = None,
    store: Any = None,
) -> Dict[str, Any]:
    """Write vector rows as JSONL (one row object per line)."""
    own = store is None
    store = store or open_vector_store(
        backend=backend,
        path=path,
        force_cloud=force_cloud,
        collection_name=collection_name,
    )
    out = Path(out_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)

    n = 0
    models: set[str] = set()
    kinds: Dict[str, int] = {}
    with out.open("w", encoding="utf-8") as fh:
        for raw in store.iter_rows(kind=kind):
            row = _as_row(raw)
            payload = {
                "schema": ROW_SCHEMA,
                **row,
            }
            if raw.get("created_at"):
                payload["created_at"] = raw["created_at"]
            fh.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
            n += 1
            if row["model"]:
                models.add(row["model"])
            kinds[row["kind"]] = kinds.get(row["kind"], 0) + 1

    if own and hasattr(store, "close"):
        store.close()

    return {
        "schema": EXPORT_SCHEMA,
        "ok": True,
        "path": str(out),
        "n_exported": n,
        "by_kind": kinds,
        "models": sorted(models),
        "source_backend": backend,
        "source_path": str(path) if path else ("chroma-cloud" if force_cloud else None),
        "exported_at": _utc_now(),
        "note": "JSONL rows use schema hyperlex.vector_row.v1; embeddings are preserved (no re-embed).",
    }


def _iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
            if not isinstance(obj, dict):
                raise ValueError(f"{path}:{lineno}: expected object")
            # skip optional manifest lines
            if obj.get("schema") == EXPORT_SCHEMA and "n_exported" in obj:
                continue
            yield obj


def import_vectors(
    *,
    in_path: Path | str,
    backend: str = "sqlite",
    path: Optional[Path | str] = None,
    force_cloud: bool = False,
    collection_name: Optional[str] = None,
    store: Any = None,
    batch_size: int = UPSERT_BATCH,
) -> Dict[str, Any]:
    """Import JSONL rows into a vector store (embeddings preserved)."""
    own = store is None
    store = store or open_vector_store(
        backend=backend,
        path=path,
        force_cloud=force_cloud,
        collection_name=collection_name,
    )
    src = Path(in_path).expanduser()
    if not src.is_file():
        raise FileNotFoundError(f"import file not found: {src}")

    batch_size = max(1, int(batch_size))
    n = 0
    batch: List[Dict[str, Any]] = []
    kinds: Dict[str, int] = {}

    def flush() -> None:
        nonlocal n, batch
        if not batch:
            return
        if hasattr(store, "upsert_many"):
            store.upsert_many(batch)
        else:
            for row in batch:
                store.upsert(**{k: row[k] for k in ("id", "kind", "text", "embedding", "model", "family_id", "meta")})
        n += len(batch)
        batch = []

    for raw in _iter_jsonl(src):
        row = _as_row(raw)
        kinds[row["kind"]] = kinds.get(row["kind"], 0) + 1
        batch.append(row)
        if len(batch) >= batch_size:
            flush()
    flush()

    stats = store.stats() if hasattr(store, "stats") else {}
    if own and hasattr(store, "close"):
        store.close()

    return {
        "schema": IMPORT_SCHEMA,
        "ok": True,
        "path": str(src),
        "n_imported": n,
        "by_kind": kinds,
        "dest_backend": backend,
        "dest_path": str(path) if path else ("chroma-cloud" if force_cloud else None),
        "dest_stats": stats,
        "imported_at": _utc_now(),
        "note": "Embeddings copied as-is (no re-embed).",
    }


def sync_vectors(
    *,
    from_backend: str = "chroma",
    from_path: Optional[Path | str] = None,
    to_backend: str = "chroma",
    to_path: Optional[Path | str] = None,
    to_cloud: bool = False,
    kind: Optional[str] = None,
    collection_name: Optional[str] = None,
    from_store: Any = None,
    to_store: Any = None,
    batch_size: int = UPSERT_BATCH,
) -> Dict[str, Any]:
    """Copy rows from one store to another (embeddings preserved).

    Typical promote::

        sync_vectors(from_backend=\"chroma\", from_path=\"~/.hyperlex/chroma\", to_cloud=True)
    """
    own_from = from_store is None
    own_to = to_store is None
    from_store = from_store or open_vector_store(
        backend=from_backend,
        path=from_path,
        force_cloud=False,
        collection_name=collection_name,
    )
    to_store = to_store or open_vector_store(
        backend=to_backend,
        path=None if to_cloud else to_path,
        force_cloud=to_cloud,
        collection_name=collection_name,
    )

    batch_size = max(1, int(batch_size))
    n = 0
    batch: List[Dict[str, Any]] = []
    kinds: Dict[str, int] = {}

    def flush() -> None:
        nonlocal n, batch
        if not batch:
            return
        to_store.upsert_many(batch)
        n += len(batch)
        batch = []

    for raw in from_store.iter_rows(kind=kind):
        row = _as_row(raw)
        kinds[row["kind"]] = kinds.get(row["kind"], 0) + 1
        batch.append(row)
        if len(batch) >= batch_size:
            flush()
    flush()

    dest_stats = to_store.stats() if hasattr(to_store, "stats") else {}
    src_stats = from_store.stats() if hasattr(from_store, "stats") else {}

    if own_from and hasattr(from_store, "close"):
        from_store.close()
    if own_to and hasattr(to_store, "close"):
        to_store.close()

    return {
        "schema": SYNC_SCHEMA,
        "ok": True,
        "n_synced": n,
        "by_kind": kinds,
        "from": {
            "backend": from_backend,
            "path": str(from_path) if from_path else None,
            "stats": src_stats,
        },
        "to": {
            "backend": to_backend,
            "path": "chroma-cloud" if to_cloud else (str(to_path) if to_path else None),
            "cloud": bool(to_cloud),
            "stats": dest_stats,
        },
        "synced_at": _utc_now(),
        "note": "Embeddings copied as-is (no re-embed). Promote path: local chroma → cloud.",
    }


def default_export_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path.home() / ".hyperlex" / "exports" / f"vectors_{stamp}.jsonl"
