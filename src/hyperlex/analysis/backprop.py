"""Lineage backpropagation — non-mutating re-match of historical receipts.

Given an expanded registry (base + YTD backfill packs), re-run
``match_lineage`` on receipt text and report family / confidence deltas.
Never rewrites receipt integrity hashes or on-disk golden files.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from . import LINEAGE_CONFIDENCE_THRESHOLD, LINEAGE_REGISTRY, match_lineage
from .backfill import apply_backfill, default_backfill_root

BACKPROP_SCHEMA = "hyperlex.lineage_backprop.v1"


def _receipt_text(receipt: Dict[str, Any]) -> str:
    """Build corpus from query + observed + matched terms + neologisms."""
    parts: List[str] = []
    q = receipt.get("query")
    if q:
        parts.append(str(q))
    observed = receipt.get("observed") or receipt.get("raw_signal") or ""
    if isinstance(observed, dict):
        observed = observed.get("text") or observed.get("signal") or json.dumps(observed)
    if observed:
        parts.append(str(observed))
    # archived summaries use observed_preview
    if receipt.get("observed_preview"):
        parts.append(str(receipt["observed_preview"]))
    analysis = receipt.get("analysis") or {}
    lin = analysis.get("lineage") or receipt.get("lineage") or {}
    for t in lin.get("matched_terms") or []:
        parts.append(str(t))
    for neo in analysis.get("neologisms") or []:
        if isinstance(neo, dict) and neo.get("term"):
            parts.append(str(neo["term"]))
        elif isinstance(neo, str):
            parts.append(neo)
    # top-level summary fields
    for t in receipt.get("matched_terms") or []:
        parts.append(str(t))
    return " ".join(parts)


def _prior_lineage(receipt: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    analysis = receipt.get("analysis") or {}
    lin = analysis.get("lineage")
    if isinstance(lin, dict) and lin.get("family_id"):
        return lin
    # sanitized archive summary
    if receipt.get("lineage_family"):
        return {
            "family_id": receipt.get("lineage_family"),
            "confidence": receipt.get("lineage_confidence"),
            "matched_terms": receipt.get("matched_terms") or [],
            "provenance": (receipt.get("epistemic") or {}).get("lineage") or "INFERRED",
        }
    return None


def _load_receipt_paths(paths: Sequence[Path]) -> List[Tuple[str, Dict[str, Any]]]:
    out: List[Tuple[str, Dict[str, Any]]] = []
    for p in paths:
        if not p.is_file() or p.suffix.lower() != ".json":
            continue
        if p.name.upper() == "MANIFEST.JSON":
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        out.append((str(p), data))
    return out


def collect_receipt_paths(
    *,
    from_golden: bool = False,
    from_archive: bool = False,
    receipt_dirs: Optional[Sequence[Path | str]] = None,
    inputs: Optional[Sequence[Path | str]] = None,
    repo_root: Optional[Path | str] = None,
    include_home: bool = False,
) -> List[Path]:
    root = Path(repo_root) if repo_root else Path.cwd()
    paths: List[Path] = []
    if from_golden:
        g = root / "examples" / "receipts" / "golden"
        if g.is_dir():
            paths.extend(sorted(g.glob("*.json")))
    if from_archive:
        a = root / "docs" / "archive" / "latest" / "receipts"
        if a.is_dir():
            paths.extend(sorted(a.glob("*.json")))
        # also index summaries if no full receipts
        idx = root / "docs" / "archive" / "latest" / "index.json"
        if idx.is_file() and not any(a.glob("*.json") for a in [a] if a.is_dir()):
            pass
    if include_home:
        home = Path.home() / ".hyperlex" / "receipts"
        if home.is_dir():
            paths.extend(sorted(home.glob("*.json")))
    for d in receipt_dirs or []:
        dp = Path(d)
        if dp.is_dir():
            paths.extend(sorted(dp.glob("*.json")))
        elif dp.is_file():
            paths.append(dp)
    for i in inputs or []:
        paths.append(Path(i))
    # de-dupe preserving order
    seen: set = set()
    uniq: List[Path] = []
    for p in paths:
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(p)
    return uniq


def rematch_receipt(
    receipt: Dict[str, Any],
    *,
    registry: Optional[Sequence[Dict[str, Any]]] = None,
    min_confidence: float = LINEAGE_CONFIDENCE_THRESHOLD,
) -> Dict[str, Any]:
    """Compare prior lineage vs rematch with optional registry overlay."""
    text = _receipt_text(receipt)
    prior = _prior_lineage(receipt)
    new = match_lineage(text, min_confidence=min_confidence, registry=registry)

    prior_fam = (prior or {}).get("family_id")
    new_fam = (new or {}).get("family_id")
    prior_conf = (prior or {}).get("confidence")
    new_conf = (new or {}).get("confidence")

    change = "unchanged"
    if prior_fam is None and new_fam is not None:
        change = "gained"
    elif prior_fam is not None and new_fam is None:
        change = "lost"
    elif prior_fam != new_fam:
        change = "reclassified"
    elif prior_fam and new_fam and prior_fam == new_fam:
        try:
            if prior_conf is not None and new_conf is not None and abs(float(new_conf) - float(prior_conf)) >= 0.02:
                change = "confidence_shift"
        except (TypeError, ValueError):
            pass

    integrity = None
    prov = receipt.get("provenance") or {}
    if isinstance(prov, dict):
        integrity = prov.get("integrity") or (prov.get("content_fingerprint") or {})
        if isinstance(integrity, dict):
            integrity = integrity.get("fingerprint_id") or integrity.get("sha256")
    integrity = integrity or receipt.get("integrity")

    return {
        "integrity": integrity,
        "query": receipt.get("query"),
        "prior_family": prior_fam,
        "prior_confidence": prior_conf,
        "prior_matched_terms": (prior or {}).get("matched_terms") or [],
        "new_family": new_fam,
        "new_confidence": new_conf,
        "new_matched_terms": (new or {}).get("matched_terms") or [],
        "change": change,
        "receipt_mutated": False,
    }


def backpropagate_lineage(
    *,
    year: int = 2026,
    through: Optional[str] = None,
    backfill_root: Optional[Path | str] = None,
    from_golden: bool = False,
    from_archive: bool = False,
    receipt_dirs: Optional[Sequence[Path | str]] = None,
    inputs: Optional[Sequence[Path | str]] = None,
    repo_root: Optional[Path | str] = None,
    include_home: bool = False,
    use_backfill: bool = True,
    min_confidence: float = LINEAGE_CONFIDENCE_THRESHOLD,
    registry: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Re-match historical receipts against expanded registry; emit report only.

    ``receipt_mutated`` is always false — integrity-preserving by design.
    """
    root = Path(repo_root) if repo_root else Path.cwd()
    bf_root = Path(backfill_root) if backfill_root else default_backfill_root(root)

    apply_report: Optional[Dict[str, Any]] = None
    if registry is not None:
        merged_reg = list(registry)
    elif use_backfill:
        apply_report = apply_backfill(year, through=through, root=bf_root)
        merged_reg = apply_report["merged_registry"]
    else:
        merged_reg = list(LINEAGE_REGISTRY)

    paths = collect_receipt_paths(
        from_golden=from_golden,
        from_archive=from_archive,
        receipt_dirs=receipt_dirs,
        inputs=inputs,
        repo_root=root,
        include_home=include_home,
    )
    loaded = _load_receipt_paths(paths)

    # If archive summaries requested without full receipt files
    if from_archive and not any("archive" in str(p) for p, _ in loaded):
        idx = root / "docs" / "archive" / "latest" / "index.json"
        if idx.is_file():
            try:
                index = json.loads(idx.read_text(encoding="utf-8"))
                for s in index.get("summaries") or []:
                    if isinstance(s, dict):
                        loaded.append((str(idx) + "#" + str(s.get("integrity") or len(loaded)), s))
            except (OSError, json.JSONDecodeError):
                pass

    rows: List[Dict[str, Any]] = []
    counts = {
        "unchanged": 0,
        "gained": 0,
        "lost": 0,
        "reclassified": 0,
        "confidence_shift": 0,
    }
    for path, receipt in loaded:
        row = rematch_receipt(receipt, registry=merged_reg, min_confidence=min_confidence)
        row["source_path"] = path
        rows.append(row)
        counts[row["change"]] = counts.get(row["change"], 0) + 1

    changed = [r for r in rows if r["change"] != "unchanged"]

    return {
        "schema": BACKPROP_SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "year": year,
        "through": through,
        "use_backfill": use_backfill,
        "n_receipts": len(rows),
        "n_changed": len(changed),
        "change_counts": counts,
        "mutates_receipts": False,
        "integrity_preserving": True,
        "brier_invented": False,
        "backfill_summary": {
            "n_packs": (apply_report or {}).get("n_packs"),
            "n_terms_added": (apply_report or {}).get("n_terms_added"),
            "merged_term_count": (apply_report or {}).get("merged_term_count"),
            "family_deltas": (apply_report or {}).get("family_deltas"),
        }
        if apply_report
        else None,
        "changes": changed,
        "rows": rows,
        "note": (
            "Lineage backpropagation re-matches only. Historical receipts and "
            "integrity hashes are not rewritten. Re-run archive-export for a new "
            "sanitized snapshot if desired."
        ),
    }
