"""Instrumentation scores and append-only watch log. Not probabilities. Not Brier."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

WATCH_SCHEMA = "hyperlex.mutation_watch.v0.2"
DEFAULT_RELATIVE = Path("mutation_watch.jsonl")

_REGISTER_W = {"none": 0.0, "low": 0.33, "med": 0.66, "high": 1.0}


def clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def watch_score(
    *,
    decode_confidence: float,
    n_ops: int,
    register_shift: str,
    irony_flag: bool,
    affix_productivity: bool,
    lexicon_hit: bool,
) -> float:
    register_w = _REGISTER_W.get(register_shift or "none", 0.0)
    lexicon_only = 1.0 if (lexicon_hit and int(n_ops) <= 1) else 0.0
    raw = (
        0.35 * float(decode_confidence)
        + 0.15 * (min(int(n_ops), 4) / 4.0)
        + 0.20 * register_w
        + 0.10 * (1.0 if irony_flag else 0.0)
        + 0.15 * (1.0 if affix_productivity else 0.0)
        + 0.15 * (0.0 if lexicon_only else 1.0)
    )
    return round(clip01(raw), 4)


def default_watch_path() -> Path:
    env = os.environ.get("HYPERLEX_MUTATION_WATCH", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / ".hyperlex" / DEFAULT_RELATIVE).resolve()


def _canonical(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def append_watch(
    packet: Dict[str, Any],
    *,
    path: Optional[Path | str] = None,
) -> Optional[Dict[str, Any]]:
    """Append one watch record. Fail-open. Never a tool-fire trigger."""
    try:
        p = Path(path) if path else default_watch_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        ops = list(packet.get("operators") or [])
        record = {
            "schema": WATCH_SCHEMA,
            "logged_at": datetime.now(timezone.utc).isoformat(),
            "packet_id": packet.get("packet_id"),
            "operators": ops,
            "layers_touched": list(packet.get("layers_touched") or []),
            "watch_score": packet.get("watch_score"),
            "n_ops": len(ops),
            "lexicon_hit": bool(packet.get("lexicon_hit")),
            "brier": None,
            "forecast_eligible": False,
            "auto_fire": False,
            "note": "instrumentation only; not a fire threshold",
        }
        with p.open("a", encoding="utf-8") as fh:
            fh.write(_canonical(record) + "\n")
        return record
    except OSError:
        return None


def read_watch_log(path: Optional[Path | str] = None) -> List[Dict[str, Any]]:
    p = Path(path) if path else default_watch_path()
    if not p.exists():
        return []
    records: List[Dict[str, Any]] = []
    try:
        with p.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(rec, dict):
                    rec["brier"] = None
                    rec["forecast_eligible"] = False
                    rec["auto_fire"] = False
                    records.append(rec)
    except OSError:
        return []
    return records


def watch_summary(
    path: Optional[Path | str] = None,
    *,
    limit: int = 20,
) -> Dict[str, Any]:
    records = read_watch_log(path)
    window = records[-max(0, int(limit)) :] if limit else records
    n = len(window)
    lex_hits = sum(1 for r in window if r.get("lexicon_hit"))
    novel_ops = ("GAME_ENCODE", "CODE_SWITCH", "PHONETIC_WARP", "AFFIX")
    novel = sum(1 for r in window if any(op in novel_ops for op in (r.get("operators") or [])))
    return {
        "ok": True,
        "command": "mutation-watch",
        "schema": WATCH_SCHEMA,
        "path": str(Path(path) if path else default_watch_path()),
        "n": len(records),
        "window": n,
        "lexicon_hit_rate": (lex_hits / n) if n else 0.0,
        "novel_operator_rate": (novel / n) if n else 0.0,
        "records": window,
        "brier": None,
        "forecast_eligible": False,
        "auto_fire": False,
        "note": "A/B rates are instrumentation. watch_score is not a fire threshold.",
    }
