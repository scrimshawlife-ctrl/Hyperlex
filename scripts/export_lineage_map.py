#!/usr/bin/env python3
"""Export interactive lineage map graph for Pages (docs/map/lineage-map.json)."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hyperlex.analysis import LINEAGE_REGISTRY  # noqa: E402

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


def build_graph() -> dict:
    first_seen = _first_seen()
    nodes: list[dict] = []
    edges: list[dict] = []

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
        for t in terms:
            tid = f"term:{fid}:{t.lower()}"
            nodes.append(
                {
                    "id": tid,
                    "kind": "term",
                    "label": t,
                    "family_id": fid,
                    "hue": meta["hue"],
                    "first_seen_month": first_seen.get(t.lower()),
                    "branch_operator": fam.get("branch_operator"),
                }
            )
            edges.append({"source": fid, "target": tid, "kind": "term_link"})

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

    return {
        "schema": "hyperlex.lineage_map.v1",
        "title": "Hyperlex slang lineage map",
        "note": "Static export from LINEAGE_REGISTRY + YTD backfill first-seen. Not a live DB.",
        "brier": None,
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "n_families": len(LINEAGE_REGISTRY),
        "n_cross_links": cross,
        "nodes": nodes,
        "edges": edges,
    }


def main() -> int:
    graph = build_graph()
    out = ROOT / "docs" / "map" / "lineage-map.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} families={graph['n_families']} nodes={graph['n_nodes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
