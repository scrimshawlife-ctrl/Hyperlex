"""signals — local high-priority attractor store.

Offline-first operator queue under ~/.hyperlex/signals/
(override via HYPERLEX_SIGNALS_DIR). Same family as receipts / score_log.
Never invents Brier. Authority remains advisory.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SIGNALS_SCHEMA = "hyperlex.signals_inbox.v1"
ATTRACTOR_RUNE_ID = "RUNE.HLX.ATTRACTOR_CANDIDATE"
# Back-compat alias for any early callers
SHADOW_RUNE_ID = ATTRACTOR_RUNE_ID


def default_signals_dir() -> Path:
    override = os.environ.get("HYPERLEX_SIGNALS_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".hyperlex" / "signals"


def _ensure_dir(path: Optional[Path] = None) -> Path:
    d = path or default_signals_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _signal_id(payload: Dict[str, Any]) -> str:
    raw = _canonical(payload)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def inbox_path(*, path: Optional[Path] = None) -> Path:
    return _ensure_dir(path) / "inbox.jsonl"


def push_signal(
    entry: Dict[str, Any],
    *,
    path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Append one signal to the local inbox. Fail-open on IO errors."""
    try:
        body = dict(entry)
        body.setdefault("schema", SIGNALS_SCHEMA)
        body.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        body.setdefault("authority", "advisory")
        if "signal_id" not in body:
            body["signal_id"] = _signal_id(body)
        p = inbox_path(path=path)
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(body, sort_keys=True, ensure_ascii=False) + "\n")
        return {"ok": True, "signal_id": body["signal_id"], "path": str(p)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def list_signals(
    *,
    path: Optional[Path] = None,
    limit: int = 50,
    min_priority: Optional[str] = None,
) -> Dict[str, Any]:
    """Read recent signals (newest last)."""
    p = inbox_path(path=path)
    if not p.is_file():
        return {"ok": True, "n": 0, "signals": [], "path": str(p)}
    rows: List[Dict[str, Any]] = []
    try:
        with p.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except Exception as exc:
        return {"ok": False, "error": str(exc), "signals": []}

    if min_priority:
        order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        thresh = order.get(str(min_priority).lower(), 0)
        rows = [
            r for r in rows
            if order.get(str(r.get("priority") or "low").lower(), 0) >= thresh
        ]
    if limit and limit > 0:
        rows = rows[-limit:]
    return {"ok": True, "n": len(rows), "signals": rows, "path": str(p)}


def clear_inbox(*, path: Optional[Path] = None, dry_run: bool = False) -> Dict[str, Any]:
    p = inbox_path(path=path)
    if not p.is_file():
        return {"ok": True, "cleared": 0, "path": str(p)}
    if dry_run:
        n = sum(1 for _ in p.open(encoding="utf-8") if _.strip())
        return {"ok": True, "cleared": 0, "would_clear": n, "dry_run": True, "path": str(p)}
    n = sum(1 for _ in p.open(encoding="utf-8") if _.strip())
    p.write_text("", encoding="utf-8")
    return {"ok": True, "cleared": n, "path": str(p)}


def build_attractor_candidate(
    result: Dict[str, Any],
    *,
    priority: str = "high",
) -> Dict[str, Any]:
    """
    Build an attractor-candidate payload from an analysis result.

    Intended for elevated hyperstition stage (ACTUALIZING) or high virality.
    Always advisory; never mutates receipts, lineage, or registry.
    """
    analysis = result.get("analysis") or {}
    prov = result.get("provenance") or {}
    hyper = analysis.get("hyperstition") or {}
    lineage = analysis.get("lineage") or {}
    virality = analysis.get("virality") or {}
    typology = (analysis.get("memetics") or {}).get("typology_primary") or (
        analysis.get("memetics") or {}
    ).get("typology")
    metrics = analysis.get("compression_metrics") or {}
    stage = str(hyper.get("loop_stage") or prov.get("hyperstition_risk") or "").upper()

    payload = {
        "schema": "hyperlex.attractor_candidate.v1",
        "rune_id": ATTRACTOR_RUNE_ID,
        "candidate_label": lineage.get("family_id") or analysis.get("primary_term") or "unknown",
        "hyperstition_stage": stage or None,
        "lineage_family": lineage.get("family_id"),
        "lineage_confidence": lineage.get("confidence"),
        "typology": typology,
        "virality_hybrid": virality.get("hybrid_score"),
        "compression_metrics": metrics,
        "observed_preview": (result.get("observed") or "")[:180],
        "inferred_preview": (result.get("inferred") or "")[:180],
        "speculative_preview": (result.get("speculative") or "")[:180],
        "priority": priority,
        "authority": "advisory",
        "brier": None,
        "note": (
            "Attractor candidate only. Operator review required before any "
            "forecast settlement or registry change."
        ),
        "source_hash": prov.get("canonical_hash"),
        "ingest_source": prov.get("ingest_source"),
    }
    return payload


# Back-compat alias
def build_shadow_candidate(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return build_attractor_candidate(*args, **kwargs)


def maybe_push_from_result(
    result: Dict[str, Any],
    *,
    path: Optional[Path] = None,
    min_stage: str = "ACTUALIZING",
    force: bool = False,
) -> Dict[str, Any]:
    """
    Auto-push an attractor candidate when hyperstition stage meets threshold.

    Default: only ACTUALIZING. Use force=True to always push.
    """
    analysis = result.get("analysis") or {}
    hyper = analysis.get("hyperstition") or {}
    prov = result.get("provenance") or {}
    stage = str(hyper.get("loop_stage") or prov.get("hyperstition_risk") or "").upper()
    stages = {"EMERGENT": 1, "ACTUALIZING": 2, "SETTLED": 3}
    if not force and stages.get(stage, 0) < stages.get(str(min_stage).upper(), 2):
        return {
            "ok": True,
            "pushed": False,
            "reason": f"stage={stage or 'none'} below min_stage={min_stage}",
        }
    candidate = build_attractor_candidate(
        result, priority="high" if stage == "ACTUALIZING" else "medium"
    )
    entry = {
        "kind": "attractor_candidate",
        "priority": candidate.get("priority"),
        "stage": stage,
        "payload": candidate,
        "query": (result.get("ingest") or {}).get("query"),
    }
    out = push_signal(entry, path=path)
    out["pushed"] = bool(out.get("ok"))
    out["stage"] = stage
    return out


__all__ = [
    "SIGNALS_SCHEMA",
    "ATTRACTOR_RUNE_ID",
    "SHADOW_RUNE_ID",  # alias
    "default_signals_dir",
    "inbox_path",
    "push_signal",
    "list_signals",
    "clear_inbox",
    "build_attractor_candidate",
    "build_shadow_candidate",  # alias
    "maybe_push_from_result",
]
