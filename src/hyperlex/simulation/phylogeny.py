"""Lightweight phylogenetic scaffold for slang families.

Builds nodes/edges from LINEAGE_REGISTRY + optional backfill first_seen months.
Domain packs under ``data/phylogeny/*.json`` overlay multi-family sketches.

Not a full linguistic phylogeny — a research-facing tree for diagrams and export.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..analysis import LINEAGE_REGISTRY
from ..analysis.backfill import default_backfill_root, inventory_backfill


def default_phylogeny_root(repo_root: Optional[Path | str] = None) -> Path:
    if repo_root is not None:
        return Path(repo_root) / "data" / "phylogeny"
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / "data" / "phylogeny",
        Path.cwd() / "data" / "phylogeny",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return candidates[0]


def list_phylogeny_families(
    registry: Optional[Sequence[Dict[str, Any]]] = None,
) -> List[str]:
    reg = list(registry) if registry is not None else LINEAGE_REGISTRY
    return [str(e.get("family_id")) for e in reg if e.get("family_id")]


def list_domain_packs(*, root: Optional[Path | str] = None) -> List[Dict[str, Any]]:
    base = Path(root) if root else default_phylogeny_root()
    if not base.is_dir():
        return []
    out: List[Dict[str, Any]] = []
    for p in sorted(base.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        out.append({
            "domain_id": data.get("domain_id") or p.stem,
            "label": data.get("label"),
            "n_families": len(data.get("families") or []),
            "n_leaves": len(data.get("leaves") or []),
            "path": str(p),
        })
    return out


def load_domain_pack(domain_id: str, *, root: Optional[Path | str] = None) -> Optional[Dict[str, Any]]:
    base = Path(root) if root else default_phylogeny_root()
    path = base / f"{domain_id}.json"
    if not path.is_file():
        # allow label match
        for p in base.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if str(data.get("domain_id") or p.stem) == domain_id:
                data["source_path"] = str(p)
                return data
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    data["source_path"] = str(path)
    return data


def build_domain_phylogeny(
    domain_id: str,
    *,
    root: Optional[Path | str] = None,
    include_family_trees: bool = True,
) -> Dict[str, Any]:
    """Merge a domain pack with per-family scaffolds."""
    pack = load_domain_pack(domain_id, root=root)
    if not pack:
        return {
            "schema": "hyperlex.domain_phylogeny.v1",
            "ok": False,
            "domain_id": domain_id,
            "error": "unknown_domain",
            "available": [p["domain_id"] for p in list_domain_packs(root=root)],
            "provenance": "INFERRED",
            "brier": None,
        }

    family_trees = []
    if include_family_trees:
        for fam in pack.get("families") or []:
            tree = build_family_phylogeny(str(fam))
            if tree.get("ok"):
                family_trees.append({
                    "family_id": fam,
                    "n_nodes": tree.get("n_nodes"),
                    "n_edges": tree.get("n_edges"),
                    "n_terms": tree.get("n_terms"),
                })

    return {
        "schema": "hyperlex.domain_phylogeny.v1",
        "ok": True,
        "domain_id": pack.get("domain_id") or domain_id,
        "label": pack.get("label"),
        "families": pack.get("families") or [],
        "roots": pack.get("roots") or [],
        "trunks": pack.get("trunks") or [],
        "leaves": pack.get("leaves") or [],
        "cross_edges": pack.get("cross_edges") or [],
        "family_trees": family_trees,
        "source_path": pack.get("source_path"),
        "provenance": pack.get("provenance_default") or "INFERRED",
        "brier": None,
        "note": "Domain overlay + family scaffolds; not a full linguistic phylogeny.",
    }


def build_family_phylogeny(
    family_id: str,
    *,
    registry: Optional[Sequence[Dict[str, Any]]] = None,
    include_backfill: bool = True,
    year: int = 2026,
    backfill_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a simple root → trunk → leaves tree for one family.

    Trunk = first half of terms (stable); leaves = remaining + backfill-only.
    """
    reg = list(registry) if registry is not None else LINEAGE_REGISTRY
    entry = next((e for e in reg if e.get("family_id") == family_id), None)
    if entry is None:
        return {
            "schema": "hyperlex.phylogeny.v1",
            "family_id": family_id,
            "ok": False,
            "error": "unknown_family",
            "provenance": "INFERRED",
        }

    terms = list(entry.get("terms") or [])
    mid = max(1, len(terms) // 2)
    trunk = terms[:mid]
    leaves = terms[mid:]

    first_seen: Dict[str, str] = {}
    if include_backfill:
        try:
            root = backfill_root or default_backfill_root()
            inv = inventory_backfill(year, root=root)
            for row in inv.get("terms") or []:
                if row.get("family_id") == family_id and row.get("term"):
                    t = str(row["term"]).lower()
                    if t not in first_seen:
                        first_seen[t] = str(row.get("first_seen_month") or "")
        except Exception:
            pass

    nodes: List[Dict[str, Any]] = [
        {
            "id": f"{family_id}::root",
            "label": f"{family_id} root",
            "kind": "root",
            "payload_note": entry.get("payload_note"),
        },
        {
            "id": f"{family_id}::trunk",
            "label": "trunk",
            "kind": "trunk",
            "terms": trunk,
        },
    ]
    edges: List[Dict[str, str]] = [
        {"source": f"{family_id}::root", "target": f"{family_id}::trunk", "operator": "stabilize"},
    ]

    for term in trunk:
        nid = f"{family_id}::term::{term}"
        nodes.append({
            "id": nid,
            "label": term,
            "kind": "trunk_term",
            "first_seen_month": first_seen.get(term.lower()),
        })
        edges.append({
            "source": f"{family_id}::trunk",
            "target": nid,
            "operator": entry.get("branch_operator") or "sense_extension",
        })

    for term in leaves:
        nid = f"{family_id}::leaf::{term}"
        nodes.append({
            "id": nid,
            "label": term,
            "kind": "leaf",
            "first_seen_month": first_seen.get(term.lower()),
        })
        edges.append({
            "source": f"{family_id}::trunk",
            "target": nid,
            "operator": entry.get("branch_operator") or "platform_compression",
        })

    return {
        "schema": "hyperlex.phylogeny.v1",
        "ok": True,
        "family_id": family_id,
        "branch_operator": entry.get("branch_operator"),
        "diagram_ref": entry.get("diagram_ref"),
        "payload_note": entry.get("payload_note"),
        "n_terms": len(terms),
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "nodes": nodes,
        "edges": edges,
        "first_seen_index": first_seen,
        "provenance": "INFERRED",
        "brier": None,
        "note": (
            "Lightweight scaffold from registry ± backfill timeline; "
            "not a full linguistic phylogeny."
        ),
    }
