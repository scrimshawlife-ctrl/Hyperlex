"""Lightweight phylogenetic scaffold for slang families.

Builds nodes/edges from LINEAGE_REGISTRY + optional backfill first_seen months.
Not a full linguistic phylogeny — a research-facing tree for diagrams and export.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from ..analysis import LINEAGE_REGISTRY
from ..analysis.backfill import default_backfill_root, inventory_backfill


def list_phylogeny_families(
    registry: Optional[Sequence[Dict[str, Any]]] = None,
) -> List[str]:
    reg = list(registry) if registry is not None else LINEAGE_REGISTRY
    return [str(e.get("family_id")) for e in reg if e.get("family_id")]


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
