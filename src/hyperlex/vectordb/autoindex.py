"""Fail-open vector indexing tied to ingest / pipeline / receipts.

Design:
  - Every successful analyze/receipt path *may* upsert into the configured
    local vector backend (sqlite or local chroma).
  - Never raises into the caller; never invents Brier; never auto-settles.
  - Cloud promote stays **manual** (``vector-sync --to cloud``) unless
    ``HYPERLEX_VECTOR_PROMOTE=1`` is set later — not the default.

Env:
  HYPERLEX_VECTOR=auto|1|0     master switch (default auto)
  HYPERLEX_VECTOR_BACKEND=sqlite|chroma
  HYPERLEX_VECTOR_DB / HYPERLEX_CHROMA_PATH
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .chroma import resolve_chroma_path
from .embed import embed_batch
from .store import default_vector_db_path


def _truthy(raw: str) -> bool:
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _falsy(raw: str) -> bool:
    return str(raw).strip().lower() in {"0", "false", "off", "no"}


def vector_flag() -> str:
    return str(os.environ.get("HYPERLEX_VECTOR", "auto")).strip().lower() or "auto"


def vector_backend() -> str:
    return str(os.environ.get("HYPERLEX_VECTOR_BACKEND", "sqlite")).strip().lower() or "sqlite"


def vector_store_path() -> Optional[Path]:
    """Local path for the active backend (None for pure Cloud with no local path)."""
    backend = vector_backend()
    if backend == "chroma":
        return resolve_chroma_path()
    return default_vector_db_path()


def vector_auto_enabled() -> bool:
    """Whether ingest should index into the local vector store."""
    flag = vector_flag()
    if _falsy(flag):
        return False
    if _truthy(flag):
        return True
    # auto: enable when a store already exists, or chroma path is configured
    backend = vector_backend()
    if backend == "chroma":
        path = resolve_chroma_path()
        if path is not None:
            return True
        # default local chroma dir if previously used
        default_chroma = Path.home() / ".hyperlex" / "chroma"
        return default_chroma.is_dir() and any(default_chroma.iterdir())
    vpath = default_vector_db_path()
    return vpath.is_file() and vpath.stat().st_size > 0


def _open_store():
    from .chroma import get_vector_store

    backend = vector_backend()
    if backend == "chroma":
        path = resolve_chroma_path() or (Path.home() / ".hyperlex" / "chroma")
        return get_vector_store(backend="chroma", path=path)
    return get_vector_store(backend="sqlite", path=default_vector_db_path())


def _id(kind: str, key: str) -> str:
    h = hashlib.sha256(f"{kind}:{key}".encode("utf-8")).hexdigest()[:24]
    return f"{kind}:{h}"


def index_texts(
    rows: Sequence[Dict[str, Any]],
    *,
    store: Any = None,
) -> Dict[str, Any]:
    """Upsert pre-shaped rows: id, kind, text, family_id?, meta?.

    Fail-open: returns ok=False on error rather than raising.
    """
    if not rows:
        return {"ok": True, "n_upserted": 0, "skipped": True}
    own = store is None
    try:
        store = store or _open_store()
        if getattr(store, "_cloud", False) or getattr(store, "force_cloud", False):
            from hyperlex.guards import require_cloud_write

            require_cloud_write()
        texts = [str(r.get("text") or "") for r in rows]
        vecs, info = embed_batch(texts)
        n = 0
        for row, vec in zip(rows, vecs):
            text = str(row.get("text") or "").strip()
            if not text:
                continue
            store.upsert(
                id=str(row["id"]),
                kind=str(row.get("kind") or "term"),
                text=text[:2000],
                embedding=vec,
                model=info.model_id,
                family_id=row.get("family_id"),
                meta={**(row.get("meta") or {}), "embed_provenance": info.provenance},
            )
            n += 1
        if own and hasattr(store, "close"):
            store.close()
        return {
            "ok": True,
            "n_upserted": n,
            "backend": vector_backend(),
            "model": info.model_id,
            "schema": "hyperlex.vector_autoindex.v1",
        }
    except Exception as exc:
        if own and store is not None and hasattr(store, "close"):
            try:
                store.close()
            except Exception:
                pass
        return {
            "ok": False,
            "error": str(exc),
            "n_upserted": 0,
            "schema": "hyperlex.vector_autoindex.v1",
        }


def index_from_analysis(
    result: Dict[str, Any],
    *,
    receipt_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Index primary term + optional receipt blob from an analyze result."""
    if not vector_auto_enabled():
        return {"ok": True, "n_upserted": 0, "skipped": True, "reason": "vector_disabled"}

    analysis = (result or {}).get("analysis") or {}
    lin = analysis.get("lineage") or {}
    ingest = (result or {}).get("ingest") or {}
    query = (
        str(ingest.get("query") or "").strip()
        or str(analysis.get("primary_term") or "").strip()
        or str((result or {}).get("query") or "").strip()
    )
    family_id = lin.get("family_id")
    matched = [str(t) for t in (lin.get("matched_terms") or []) if str(t).strip()]
    rows: List[Dict[str, Any]] = []

    # Index atomic terms seen on this ingest
    terms: List[str] = []
    primary = str(analysis.get("primary_term") or "").strip()
    if primary:
        terms.append(primary)
    for t in matched[:12]:
        if t not in terms:
            terms.append(t)
    if query and query not in terms and len(query.split()) <= 4:
        terms.append(query)

    for t in terms:
        rows.append({
            "id": _id("term", f"ingest:{family_id or ''}:{t.lower()}"),
            "kind": "term",
            "text": t,
            "family_id": family_id,
            "meta": {
                "source": "ingest_autoindex",
                "query": query,
                "lineage_confidence": lin.get("confidence"),
            },
        })

    if receipt_path:
        try:
            import json

            p = Path(receipt_path)
            data = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else result
        except Exception:
            data = result
        observed = str((data or {}).get("observed") or (result or {}).get("observed") or "")[:400]
        text = " ".join(x for x in [query, observed, " ".join(matched[:12])] if x).strip()
        if text:
            integ = ((data or {}).get("receipt") or {}).get("integrity") or (
                Path(str(receipt_path)).stem if receipt_path else "live"
            )
            rows.append({
                "id": _id("receipt", str(integ)),
                "kind": "receipt",
                "text": text,
                "family_id": family_id,
                "meta": {
                    "source": "ingest_autoindex",
                    "integrity": integ,
                    "path": str(receipt_path) if receipt_path else None,
                    "query": query,
                },
            })

    return index_texts(rows)


def index_receipt_path(path: Path | str) -> Dict[str, Any]:
    """Index a single on-disk receipt (used by emit_receipt)."""
    if not vector_auto_enabled():
        return {"ok": True, "n_upserted": 0, "skipped": True, "reason": "vector_disabled"}
    try:
        import json

        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"ok": False, "error": "receipt not object", "n_upserted": 0}
        return index_from_analysis(data, receipt_path=p)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "n_upserted": 0}
