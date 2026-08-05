"""Seed the vector DB from registry, backfill packs, and receipts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..analysis import LINEAGE_REGISTRY
from ..analysis.backfill import default_backfill_root, inventory_backfill
from .embed import embed_batch
from .store import VectorStore, default_vector_db_path


def _id(kind: str, key: str) -> str:
    h = hashlib.sha256(f"{kind}:{key}".encode("utf-8")).hexdigest()[:24]
    return f"{kind}:{h}"


def seed_from_registry(
    store: Optional[VectorStore] = None,
    *,
    registry: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    own = store is None
    store = store or VectorStore()
    reg = list(registry) if registry is not None else LINEAGE_REGISTRY
    texts: List[str] = []
    meta_rows: List[Dict[str, Any]] = []
    for entry in reg:
        fam = str(entry.get("family_id") or "")
        for term in entry.get("terms") or []:
            t = str(term).strip()
            if not t:
                continue
            texts.append(t)
            meta_rows.append({
                "id": _id("term", f"{fam}:{t.lower()}"),
                "kind": "term",
                "text": t,
                "family_id": fam,
                "meta": {
                    "source": "LINEAGE_REGISTRY",
                    "branch_operator": entry.get("branch_operator"),
                },
            })
    if not texts:
        if own:
            store.close()
        return {"ok": True, "n_upserted": 0, "source": "registry"}

    vecs, info = embed_batch(texts)
    for row, vec in zip(meta_rows, vecs):
        store.upsert(
            id=row["id"],
            kind=row["kind"],
            text=row["text"],
            embedding=vec,
            model=info.model_id,
            family_id=row.get("family_id"),
            meta={**row.get("meta", {}), "embed_provenance": info.provenance},
        )
    if own:
        store.close()
    return {
        "ok": True,
        "n_upserted": len(meta_rows),
        "source": "registry",
        "model": info.model_id,
        "dim": info.dim,
    }


def seed_from_backfill(
    store: Optional[VectorStore] = None,
    *,
    year: int = 2026,
    through: Optional[str] = None,
    backfill_root: Optional[Path | str] = None,
) -> Dict[str, Any]:
    own = store is None
    store = store or VectorStore()
    root = Path(backfill_root) if backfill_root else default_backfill_root()
    inv = inventory_backfill(year, root=root, through=through)
    texts: List[str] = []
    meta_rows: List[Dict[str, Any]] = []
    for row in inv.get("terms") or []:
        t = str(row.get("term") or "").strip()
        if not t:
            continue
        fam = str(row.get("family_id") or "")
        texts.append(t)
        meta_rows.append({
            "id": _id("term", f"backfill:{fam}:{t.lower()}"),
            "kind": "term",
            "text": t,
            "family_id": fam or None,
            "meta": {
                "source": "backfill",
                "pack_label": row.get("pack_label") or row.get("first_seen_month"),
                "prominence": row.get("prominence"),
                "provenance": row.get("provenance"),
                "first_seen_month": row.get("first_seen_month"),
            },
        })
    if not texts:
        if own:
            store.close()
        return {"ok": True, "n_upserted": 0, "source": "backfill", "n_packs": inv.get("n_packs")}

    # batch in chunks of 64
    n = 0
    model_id = None
    dim = None
    for i in range(0, len(texts), 64):
        chunk_t = texts[i : i + 64]
        chunk_m = meta_rows[i : i + 64]
        vecs, info = embed_batch(chunk_t)
        model_id = info.model_id
        dim = info.dim
        for row, vec in zip(chunk_m, vecs):
            store.upsert(
                id=row["id"],
                kind=row["kind"],
                text=row["text"],
                embedding=vec,
                model=info.model_id,
                family_id=row.get("family_id"),
                meta={**row.get("meta", {}), "embed_provenance": info.provenance},
            )
            n += 1
    if own:
        store.close()
    return {
        "ok": True,
        "n_upserted": n,
        "source": "backfill",
        "n_packs": inv.get("n_packs"),
        "model": model_id,
        "dim": dim,
    }


def seed_from_receipts(
    store: Optional[VectorStore] = None,
    *,
    receipt_dirs: Optional[Sequence[Path | str]] = None,
    include_home: bool = True,
    limit: int = 500,
) -> Dict[str, Any]:
    own = store is None
    store = store or VectorStore()
    paths: List[Path] = []
    for d in receipt_dirs or []:
        dp = Path(d)
        if dp.is_dir():
            paths.extend(sorted(dp.glob("*.json")))
        elif dp.is_file():
            paths.append(dp)
    if include_home:
        home = Path.home() / ".hyperlex" / "receipts"
        if home.is_dir():
            paths.extend(sorted(home.glob("*.json")))
    # de-dupe
    seen = set()
    uniq: List[Path] = []
    for p in paths:
        k = str(p.resolve()) if p.exists() else str(p)
        if k in seen:
            continue
        seen.add(k)
        uniq.append(p)
    uniq = uniq[: max(0, int(limit))]

    texts: List[str] = []
    meta_rows: List[Dict[str, Any]] = []
    for p in uniq:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        analysis = data.get("analysis") or {}
        lin = analysis.get("lineage") or {}
        q = (data.get("ingest") or {}).get("query") or data.get("query") or ""
        observed = str(data.get("observed") or "")[:400]
        terms = " ".join(str(t) for t in (lin.get("matched_terms") or [])[:12])
        text = " ".join(x for x in [str(q), observed, terms] if x).strip()
        if not text:
            continue
        integ = (data.get("receipt") or {}).get("integrity") or p.stem
        texts.append(text)
        meta_rows.append({
            "id": _id("receipt", str(integ)),
            "kind": "receipt",
            "text": text,
            "family_id": lin.get("family_id"),
            "meta": {
                "source": "receipt",
                "integrity": integ,
                "path": str(p),
                "lineage_confidence": lin.get("confidence"),
                "query": q,
            },
        })

    n = 0
    model_id = None
    dim = None
    for i in range(0, len(texts), 32):
        chunk_t = texts[i : i + 32]
        chunk_m = meta_rows[i : i + 32]
        vecs, info = embed_batch(chunk_t)
        model_id = info.model_id
        dim = info.dim
        for row, vec in zip(chunk_m, vecs):
            store.upsert(
                id=row["id"],
                kind=row["kind"],
                text=row["text"][:2000],
                embedding=vec,
                model=info.model_id,
                family_id=row.get("family_id"),
                meta={**row.get("meta", {}), "embed_provenance": info.provenance},
            )
            n += 1
    if own:
        store.close()
    return {
        "ok": True,
        "n_upserted": n,
        "source": "receipts",
        "n_files_scanned": len(uniq),
        "model": model_id,
        "dim": dim,
    }


def seed_all(
    *,
    path: Optional[Path | str] = None,
    year: int = 2026,
    through: Optional[str] = "2026-08",
    backfill_root: Optional[Path | str] = None,
    receipt_dirs: Optional[Sequence[Path | str]] = None,
    include_home: bool = True,
    include_registry: bool = True,
    include_backfill: bool = True,
    include_receipts: bool = True,
) -> Dict[str, Any]:
    store = VectorStore(path)
    parts = []
    if include_registry:
        parts.append(seed_from_registry(store))
    if include_backfill:
        parts.append(seed_from_backfill(store, year=year, through=through, backfill_root=backfill_root))
    if include_receipts:
        parts.append(seed_from_receipts(store, receipt_dirs=receipt_dirs, include_home=include_home))
    stats = store.stats()
    store.close()
    return {
        "schema": "hyperlex.vector_seed.v1",
        "ok": True,
        "path": str(Path(path) if path else default_vector_db_path()),
        "parts": parts,
        "stats": stats,
        "note": "Local SQLite vector DB. Default embedder is deterministic hash (offline).",
    }
