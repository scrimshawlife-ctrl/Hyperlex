"""Live slang ingest → Spec 007 dataset candidates.

SHADOW only. No hyperlex import. No Brier. No OBSERVED promotion.
Live atoms stay INFERRED until an operator settles them.

Local store (not git):
  ~/.hyperlex/hyperlexical/ingest_candidates.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .export import COLLISION_HOLD, FAMILIES, TYPOLOGY, _row, lexical_split
from .packet import RESTRICTED_MARKER

STORE_SCHEMA = "hyperlex.hyperlexical.ingest_candidate.v0.1"
DEFAULT_STORE = Path.home() / ".hyperlex" / "hyperlexical" / "ingest_candidates.jsonl"
MAX_TEXT = 256


def store_path(explicit: str | Path | None = None) -> Path:
    if explicit:
        return Path(explicit)
    env = os.environ.get("HYPERLEX_HYPERLEXICAL_STORE")
    if env:
        return Path(env)
    return DEFAULT_STORE


def _clip(text: str) -> str:
    raw = " ".join((text or "").split())
    if len(raw) <= MAX_TEXT:
        return raw
    return raw[: MAX_TEXT - 1].rstrip() + "…"


def _family(raw: Any) -> str:
    fam = str(raw or "").strip() or "none"
    if fam == "ytd_leaf":
        return "ytd_leaf"
    if fam in FAMILIES:
        return fam
    return "none"


def _stage(raw: Any) -> str:
    val = str(raw or "").strip().lower()
    mapping = {
        "noise": "noise",
        "circulating": "circulating",
        "contested": "contested",
        "emergent": "circulating",
        "actualizing": "hyperstition_ish",
        "hyperstition_ish": "hyperstition_ish",
        "hyperstition": "hyperstition_ish",
    }
    return mapping.get(val, "circulating")


def _atoms_from_analysis(result: dict[str, Any], query: str = "") -> list[str]:
    analysis = result.get("analysis") or {}
    lineage = analysis.get("lineage") or {}
    ingest = result.get("ingest") or {}
    terms: list[str] = []
    for item in lineage.get("matched_terms") or []:
        if isinstance(item, str) and item.strip():
            terms.append(item.strip())
        elif isinstance(item, dict):
            t = str(item.get("term") or item.get("text") or "").strip()
            if t:
                terms.append(t)
    primary = str(analysis.get("primary_term") or "").strip()
    if primary:
        terms.append(primary)
    q = str(query or ingest.get("query") or result.get("query") or "").strip()
    if q:
        terms.append(q)
    neo = analysis.get("neologisms") or []
    if isinstance(neo, list):
        for item in neo:
            if isinstance(item, str) and item.strip():
                terms.append(item.strip())
            elif isinstance(item, dict):
                t = str(item.get("term") or item.get("surface") or "").strip()
                if t:
                    terms.append(t)
    seen: set[str] = set()
    out: list[str] = []
    for term in terms:
        clipped = _clip(term)
        key = clipped.lower()
        if not clipped or key in seen:
            continue
        seen.add(key)
        out.append(clipped)
    return out


def row_from_atom(
    text: str,
    *,
    family: str = "none",
    source: str = "pipeline",
    stage: str | None = None,
) -> dict[str, Any] | None:
    clipped = _clip(text)
    if not clipped:
        return None
    if RESTRICTED_MARKER in clipped:
        return None
    fam = _family(family)
    if clipped.lower() in COLLISION_HOLD:
        fam = "none"
    return _row(
        text=clipped,
        lineage=fam,
        typology=TYPOLOGY.get(fam, []),
        stage=_stage(stage),
        task="classify",
        provenance=f"ingest:{source}",
        **{"class": "INFERRED"},
        role_scheme=None,
        split=lexical_split(clipped),
        license="operator-local",
    )


def rows_from_analysis(result: dict[str, Any], query: str = "", source: str = "pipeline") -> list[dict[str, Any]]:
    analysis = result.get("analysis") or {}
    lineage = analysis.get("lineage") or {}
    hyper = analysis.get("hyperstition") or {}
    fam = lineage.get("family_id") or "none"
    stage = hyper.get("loop_stage") or hyper.get("stage")
    rows = []
    for atom in _atoms_from_analysis(result, query=query):
        row = row_from_atom(atom, family=fam, source=source, stage=stage)
        if row:
            rows.append(row)
    return rows


def rows_from_pipeline_packet(packet: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    units = packet.get("results")
    if isinstance(units, list) and units:
        for unit in units:
            if not isinstance(unit, dict):
                continue
            result = unit.get("result") if isinstance(unit.get("result"), dict) else unit
            rows.extend(rows_from_analysis(result, query=str(unit.get("query") or ""), source="pipeline"))
        return rows
    if isinstance(packet.get("result"), dict):
        return rows_from_analysis(packet["result"], query=str(packet.get("query") or packet.get("input") or ""), source="pipeline")
    if "analysis" in packet:
        return rows_from_analysis(packet, query=str(packet.get("query") or ""), source="pipeline")
    return rows


def rows_from_inbox(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(item, dict):
            continue
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else item
        text = str(
            payload.get("term")
            or payload.get("text")
            or payload.get("query")
            or item.get("term")
            or ""
        ).strip()
        fam = payload.get("lineage_family") or payload.get("family_id") or "none"
        row = row_from_atom(text, family=str(fam), source="inbox")
        if row:
            rows.append(row)
    return rows


def load_store(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and item.get("text"):
            rows.append(item)
    return rows


def append_rows(rows: Iterable[dict[str, Any]], path: Path | None = None) -> dict[str, Any]:
    dest = store_path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    existing = load_store(dest)
    seen = {(r.get("task"), r.get("text"), r.get("role_scheme"), r.get("lineage")) for r in existing}
    added = 0
    with dest.open("a", encoding="utf-8") as fh:
        for row in rows:
            key = (row.get("task"), row.get("text"), row.get("role_scheme"), row.get("lineage"))
            if key in seen:
                continue
            seen.add(key)
            fh.write(json.dumps(row, sort_keys=True) + "\n")
            added += 1
    return {
        "schema": STORE_SCHEMA,
        "ok": True,
        "store": str(dest),
        "added": added,
        "total": len(seen),
        "class": "INFERRED",
        "brier": None,
        "name_gate": False,
        "written_at": datetime.now(timezone.utc).isoformat(),
    }


def tap_analysis(result: dict[str, Any], query: str = "", source: str = "pipeline") -> dict[str, Any]:
    """Fail-open hook for pipeline / analyze / scan."""
    try:
        rows = rows_from_analysis(result, query=query, source=source)
        if not rows:
            return {"ok": True, "added": 0, "brier": None, "skipped": True}
        return append_rows(rows)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "brier": None, "fail_open": True}


def harvest_store(path: Path | None = None) -> list[dict[str, Any]]:
    rows = []
    for raw in load_store(store_path(path)):
        text = str(raw.get("text") or "")
        if not text or RESTRICTED_MARKER in text:
            continue
        fam = _family(raw.get("lineage"))
        rebuilt = row_from_atom(
            text,
            family=fam,
            source="store",
            stage=raw.get("stage"),
        )
        if rebuilt:
            rows.append(rebuilt)
    return rows


def counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    classify = [r for r in rows if r.get("task") == "classify"]
    return {
        "n": len(rows),
        "classify": len(classify),
        "families": sorted({r.get("lineage") for r in classify if r.get("lineage")}),
        "observed": sum(1 for r in rows if r.get("class") == "OBSERVED"),
        "inferred": sum(1 for r in rows if r.get("class") == "INFERRED"),
        "name_gate": False,
        "brier": None,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="hyperlexical-ingest-tap")
    p.add_argument("--from-json", default="", help="pipeline / analyze packet")
    p.add_argument("--from-stdin", action="store_true")
    p.add_argument("--inbox", default="", help="signals inbox jsonl")
    p.add_argument("--store", default="", help="candidate jsonl path")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    rows: list[dict[str, Any]] = []
    if args.from_json:
        packet = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        rows.extend(rows_from_pipeline_packet(packet))
    if args.from_stdin:
        raw = sys.stdin.read()
        if raw.strip():
            rows.extend(rows_from_pipeline_packet(json.loads(raw)))
    inbox = Path(args.inbox) if args.inbox else Path.home() / ".hyperlex" / "signals" / "inbox.jsonl"
    if inbox.is_file():
        rows.extend(rows_from_inbox(inbox))

    seen = set()
    unique = []
    for row in rows:
        key = (row["task"], row["text"], row.get("role_scheme"), row["lineage"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)

    dest = store_path(args.store or None)
    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "counts": counts(unique), "brier": None}, indent=2))
        return 0
    report = append_rows(unique, dest)
    report["counts"] = counts(unique)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
