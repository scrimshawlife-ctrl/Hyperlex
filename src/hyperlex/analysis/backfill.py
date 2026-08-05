"""YTD slang backfill packs — load, inventory, merge into lineage registry.

Packs live under ``data/backfill/YYYY/`` (repo root). They are curated seeds
with OBSERVED/INFERRED/SPECULATIVE labels, not a live crawl corpus.

Applying packs never rewrites historical receipt integrity. Use
``hyperlex.analysis.backprop`` to re-match receipts against a merged registry
and emit a reclassification report.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from . import LINEAGE_REGISTRY

BACKFILL_SCHEMA = "hyperlex.backfill_pack.v1"
BACKFILL_INVENTORY_SCHEMA = "hyperlex.backfill_inventory.v1"


def default_backfill_root(repo_root: Optional[Path | str] = None) -> Path:
    """Resolve ``data/backfill`` from package, CWD, or explicit repo root."""
    if repo_root is not None:
        return Path(repo_root) / "data" / "backfill"
    # src/hyperlex/analysis/backfill.py → parents[3] = repo root when editable
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / "data" / "backfill",  # .../repo/src/hyperlex/analysis
        Path.cwd() / "data" / "backfill",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return candidates[0]


def _parse_label(label: str) -> Tuple[int, int]:
    """Parse 'YYYY-MM' → (year, month)."""
    parts = label.strip().split("-")
    if len(parts) != 2:
        raise ValueError(f"invalid month label: {label!r}")
    return int(parts[0]), int(parts[1])


def load_backfill_pack(path: Path | str) -> Dict[str, Any]:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"pack root must be object: {p}")
    data.setdefault("schema", BACKFILL_SCHEMA)
    data.setdefault("source_path", str(p))
    if "terms" not in data or not isinstance(data["terms"], list):
        raise ValueError(f"pack missing terms[]: {p}")
    return data


def list_backfill_packs(
    year: int = 2026,
    *,
    root: Optional[Path | str] = None,
    through: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Load packs for ``year``, optionally capped by ``through`` (YYYY-MM)."""
    base = Path(root) if root else default_backfill_root()
    year_dir = base / str(year)
    if not year_dir.is_dir():
        return []

    through_ym: Optional[Tuple[int, int]] = None
    if through:
        through_ym = _parse_label(through)

    packs: List[Dict[str, Any]] = []
    for path in sorted(year_dir.glob("*.json")):
        if path.name.upper() == "README.JSON":
            continue
        try:
            pack = load_backfill_pack(path)
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        y = int(pack.get("year") or year)
        m = int(pack.get("month") or 0)
        if y != year:
            continue
        if through_ym is not None:
            if (y, m) > through_ym:
                continue
        packs.append(pack)
    packs.sort(key=lambda p: (int(p.get("year", 0)), int(p.get("month", 0))))
    return packs


def inventory_backfill(
    year: int = 2026,
    *,
    root: Optional[Path | str] = None,
    through: Optional[str] = None,
) -> Dict[str, Any]:
    """Summarize packs: term counts, families, provenance mix."""
    packs = list_backfill_packs(year, root=root, through=through)
    by_family: Dict[str, int] = {}
    by_provenance: Dict[str, int] = {}
    by_prominence: Dict[str, int] = {}
    terms_flat: List[Dict[str, Any]] = []
    seen_keys: set = set()

    for pack in packs:
        label = pack.get("label") or f"{pack.get('year')}-{int(pack.get('month', 0)):02d}"
        default_prov = pack.get("provenance_default") or "INFERRED"
        for t in pack.get("terms") or []:
            if not isinstance(t, dict):
                continue
            term = str(t.get("term") or "").strip()
            if not term:
                continue
            fam = str(t.get("family_id") or "unknown")
            prov = str(t.get("provenance") or default_prov)
            prom = str(t.get("prominence") or "medium")
            key = (term.lower(), fam)
            row = {
                "term": term,
                "family_id": fam,
                "first_seen_month": t.get("first_seen_month") or label,
                "prominence": prom,
                "provenance": prov,
                "branch_operator": t.get("branch_operator"),
                "pack_label": label,
                "notes": t.get("notes"),
            }
            terms_flat.append(row)
            if key not in seen_keys:
                seen_keys.add(key)
                by_family[fam] = by_family.get(fam, 0) + 1
            by_provenance[prov] = by_provenance.get(prov, 0) + 1
            by_prominence[prom] = by_prominence.get(prom, 0) + 1

    return {
        "schema": BACKFILL_INVENTORY_SCHEMA,
        "year": year,
        "through": through,
        "n_packs": len(packs),
        "pack_labels": [p.get("label") for p in packs],
        "n_term_entries": len(terms_flat),
        "n_unique_term_family": len(seen_keys),
        "by_family": dict(sorted(by_family.items())),
        "by_provenance": dict(sorted(by_provenance.items())),
        "by_prominence": dict(sorted(by_prominence.items())),
        "terms": terms_flat,
        "packs": [
            {
                "label": p.get("label"),
                "year": p.get("year"),
                "month": p.get("month"),
                "n_terms": len(p.get("terms") or []),
                "notes": p.get("notes"),
                "source_path": p.get("source_path"),
            }
            for p in packs
        ],
    }


def terms_for_family(
    packs: Sequence[Dict[str, Any]],
    family_id: str,
) -> List[str]:
    """Collect unique terms for one family across packs (order preserved)."""
    out: List[str] = []
    seen: set = set()
    for pack in packs:
        for t in pack.get("terms") or []:
            if not isinstance(t, dict):
                continue
            if str(t.get("family_id") or "") != family_id:
                continue
            term = str(t.get("term") or "").strip()
            if not term:
                continue
            key = term.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(term)
    return out


def merge_registry_with_packs(
    packs: Sequence[Dict[str, Any]],
    *,
    base_registry: Optional[Sequence[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Return a deep-copied registry with pack terms unioned into matching families.

    Does not mutate ``LINEAGE_REGISTRY`` or ``base_registry``.
    New families appearing only in packs are appended.
    """
    registry = copy.deepcopy(list(base_registry if base_registry is not None else LINEAGE_REGISTRY))
    by_id = {str(e.get("family_id")): e for e in registry}

    for pack in packs:
        label = pack.get("label") or ""
        for t in pack.get("terms") or []:
            if not isinstance(t, dict):
                continue
            term = str(t.get("term") or "").strip()
            fam = str(t.get("family_id") or "").strip()
            if not term or not fam:
                continue
            entry = by_id.get(fam)
            if entry is None:
                entry = {
                    "family_id": fam,
                    "terms": [],
                    "branch_operator": t.get("branch_operator") or "unknown",
                    "diagram_ref": None,
                    "payload_note": f"backfill-only family from packs ({label})",
                    "backfill_origin": True,
                }
                registry.append(entry)
                by_id[fam] = entry
            terms: List[str] = list(entry.get("terms") or [])
            lower = {x.lower() for x in terms}
            if term.lower() not in lower:
                terms.append(term)
                entry["terms"] = terms
            # track backfill metadata lightly
            meta = entry.setdefault("backfill_terms", {})
            meta[term.lower()] = {
                "first_seen_month": t.get("first_seen_month") or label,
                "provenance": t.get("provenance") or pack.get("provenance_default") or "INFERRED",
                "prominence": t.get("prominence") or "medium",
            }

    return registry


def apply_backfill(
    year: int = 2026,
    *,
    through: Optional[str] = None,
    root: Optional[Path | str] = None,
    base_registry: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Load packs and produce a merged registry + inventory (non-mutating global).

    Returns report suitable for CLI JSON.
    """
    packs = list_backfill_packs(year, root=root, through=through)
    inv = inventory_backfill(year, root=root, through=through)
    base = list(base_registry if base_registry is not None else LINEAGE_REGISTRY)
    merged = merge_registry_with_packs(packs, base_registry=base)

    base_term_count = sum(len(e.get("terms") or []) for e in base)
    merged_term_count = sum(len(e.get("terms") or []) for e in merged)
    added = merged_term_count - base_term_count

    family_deltas: Dict[str, Dict[str, Any]] = {}
    base_by = {e["family_id"]: set(x.lower() for x in (e.get("terms") or [])) for e in base}
    for e in merged:
        fid = e["family_id"]
        now = set(x.lower() for x in (e.get("terms") or []))
        before = base_by.get(fid, set())
        new_terms = sorted(now - before)
        if new_terms or fid not in base_by:
            family_deltas[fid] = {
                "n_before": len(before),
                "n_after": len(now),
                "added_terms": new_terms,
            }

    return {
        "schema": "hyperlex.backfill_apply.v1",
        "year": year,
        "through": through or inv.get("pack_labels", [None])[-1] if inv.get("pack_labels") else through,
        "n_packs": len(packs),
        "base_term_count": base_term_count,
        "merged_term_count": merged_term_count,
        "n_terms_added": added,
        "family_deltas": family_deltas,
        "inventory": {
            "n_term_entries": inv["n_term_entries"],
            "n_unique_term_family": inv["n_unique_term_family"],
            "by_family": inv["by_family"],
            "by_provenance": inv["by_provenance"],
            "pack_labels": inv["pack_labels"],
        },
        "merged_registry": merged,
        "mutates_receipts": False,
        "note": "Merged registry is in-memory only; historical receipts are not rewritten.",
    }
