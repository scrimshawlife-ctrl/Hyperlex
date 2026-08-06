#!/usr/bin/env python3
"""Export interactive lineage map graph for Pages (docs/map/lineage-map.json).

Includes:
  - families + terms from LINEAGE_REGISTRY
  - first-seen months from YTD backfill packs
  - within-family hash-embed neighbor hints (INFERRED; not Brier)
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hyperlex.analysis import LINEAGE_REGISTRY  # noqa: E402
from hyperlex.vectordb.embed import cosine, embed_hash  # noqa: E402

META = {
    "betting-sharp": {"label": "Betting / Sharp", "domain": "betting", "hue": 350},
    "crypto-degen": {"label": "Crypto / Degen", "domain": "crypto", "hue": 45},
    "ai-native": {"label": "AI-native", "domain": "ai", "hue": 200},
    "brainrot-aura": {"label": "Brainrot / Aura", "domain": "internet", "hue": 300},
    "kinship-address": {"label": "Kinship", "domain": "social", "hue": 140},
    "political-status": {"label": "Political status", "domain": "politics", "hue": 15},
    "gaming-meta": {"label": "Gaming / Meta", "domain": "gaming", "hue": 170},
    "workplace-corp": {"label": "Workplace / Corp", "domain": "labor", "hue": 80},
}

NEIGHBOR_TOP_K = 3
NEIGHBOR_MIN_SCORE = 0.08


def _first_seen() -> dict[str, str]:
    out: dict[str, str] = {}
    backfill = ROOT / "data" / "backfill" / "2026"
    if not backfill.is_dir():
        return out
    for p in sorted(backfill.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        month = str(data.get("month") or p.stem)
        for row in data.get("terms") or []:
            term = str(row.get("term") or "").strip().lower()
            if term and term not in out:
                out[term] = month
    return out


def _within_family_neighbors(terms: list[str]) -> dict[str, list[dict]]:
    """Top-k hash-embed neighbors inside one family (INFERRED)."""
    if len(terms) < 2:
        return {}
    vecs = {t: embed_hash(t) for t in terms}
    out: dict[str, list[dict]] = {}
    for t in terms:
        scored = []
        for u in terms:
            if u == t:
                continue
            s = float(cosine(vecs[t], vecs[u]))
            if s >= NEIGHBOR_MIN_SCORE:
                scored.append((u, round(s, 4)))
        scored.sort(key=lambda x: -x[1])
        out[t] = [{"term": u, "score": sc} for u, sc in scored[:NEIGHBOR_TOP_K]]
    return out


def build_graph() -> dict:
    first_seen = _first_seen()
    nodes: list[dict] = []
    edges: list[dict] = []
    neighbor_edges: list[dict] = []

    n_terms = sum(len(f.get("terms") or []) for f in LINEAGE_REGISTRY)
    nodes.append(
        {
            "id": "hyperlex",
            "kind": "root",
            "label": "Hyperlex slang",
            "n_terms": n_terms,
            "n_families": len(LINEAGE_REGISTRY),
        }
    )

    for fam in LINEAGE_REGISTRY:
        fid = str(fam["family_id"])
        meta = META.get(fid, {"label": fid, "domain": "other", "hue": 220})
        terms = [str(t) for t in (fam.get("terms") or [])]
        neighbors = _within_family_neighbors(terms)
        nodes.append(
            {
                "id": fid,
                "kind": "family",
                "label": meta["label"],
                "family_id": fid,
                "domain": meta["domain"],
                "hue": meta["hue"],
                "branch_operator": fam.get("branch_operator"),
                "payload_note": fam.get("payload_note"),
                "diagram_ref": fam.get("diagram_ref"),
                "n_terms": len(terms),
            }
        )
        edges.append({"source": "hyperlex", "target": fid, "kind": "family_link"})
        term_ids = {}
        for t in terms:
            tid = f"term:{fid}:{t.lower()}"
            term_ids[t.lower()] = tid
            nodes.append(
                {
                    "id": tid,
                    "kind": "term",
                    "label": t,
                    "family_id": fid,
                    "hue": meta["hue"],
                    "first_seen_month": first_seen.get(t.lower()),
                    "branch_operator": fam.get("branch_operator"),
                    "neighbors": neighbors.get(t, []),
                }
            )
            edges.append({"source": fid, "target": tid, "kind": "term_link"})
        # undirected neighbor edges (dedupe by sorted pair)
        seen_pairs: set[tuple[str, str]] = set()
        for t, neighs in neighbors.items():
            a = term_ids[t.lower()]
            for n in neighs:
                b = term_ids.get(str(n["term"]).lower())
                if not b:
                    continue
                pair = tuple(sorted((a, b)))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                neighbor_edges.append(
                    {
                        "source": pair[0],
                        "target": pair[1],
                        "kind": "embed_neighbor",
                        "score": n["score"],
                        "family_id": fid,
                        "provenance": "INFERRED",
                        "note": "hash embed cosine within family; not Brier",
                    }
                )

    by_term: dict[str, list[str]] = defaultdict(list)
    for n in nodes:
        if n["kind"] == "term":
            by_term[n["label"].lower()].append(n["id"])
    cross = 0
    for term, ids in by_term.items():
        if len(ids) < 2:
            continue
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                edges.append(
                    {
                        "source": ids[i],
                        "target": ids[j],
                        "kind": "cross_family",
                        "term": term,
                    }
                )
                cross += 1

    edges.extend(neighbor_edges)
    return {
        "schema": "hyperlex.lineage_map.v1",
        "title": "Hyperlex slang lineage map",
        "note": "Static export from LINEAGE_REGISTRY + YTD backfill first-seen + within-family hash neighbors.",
        "brier": None,
        "embed_model": "hyperlex.hash_ngram_v1.d256",
        "embed_provenance": "INFERRED",
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "n_families": len(LINEAGE_REGISTRY),
        "n_cross_links": cross,
        "n_neighbor_edges": len(neighbor_edges),
        "nodes": nodes,
        "edges": edges,
    }


def main() -> int:
    graph = build_graph()
    out = ROOT / "docs" / "map" / "lineage-map.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {out} families={graph['n_families']} nodes={graph['n_nodes']} "
        f"neighbors={graph['n_neighbor_edges']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
