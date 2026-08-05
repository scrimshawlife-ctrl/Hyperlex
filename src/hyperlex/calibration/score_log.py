"""Append-only, hash-chained score log for Hyperlex calibration.

Default location: ~/.hyperlex/score_log.jsonl
Override: HYPERLEX_SCORE_LOG env, or explicit path argument.
Repo-local alternative: out/calibration/score_log.jsonl

Events:
  forecast   — extracted forecast stored for later settlement
  settlement — operator/automated settlement decision
  score      — atomic score_pair result (only when settlement is scorable)

Series scores are never stored as truth; recompute via recompute_series().
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .scoring import score_pair, score_series
from .settlement import is_scorable

SCHEMA = "hyperlex.score_log.v1"
GENESIS_HASH = "0" * 64
DEFAULT_RELATIVE = Path("score_log.jsonl")


def default_log_path() -> Path:
    """Resolve score log path: env > ~/.hyperlex/score_log.jsonl."""
    env = os.environ.get("HYPERLEX_SCORE_LOG", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / ".hyperlex" / DEFAULT_RELATIVE).resolve()


def repo_log_path(repo_root: Path | str) -> Path:
    return (Path(repo_root) / "out" / "calibration" / DEFAULT_RELATIVE).resolve()


def _canonical(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash_payload(obj: Dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _last_record_hash(path: Path) -> str:
    if not path.exists() or path.stat().st_size == 0:
        return GENESIS_HASH
    last = ""
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                last = line
    if not last:
        return GENESIS_HASH
    try:
        rec = json.loads(last)
        return str(rec.get("record_hash") or GENESIS_HASH)
    except json.JSONDecodeError:
        return GENESIS_HASH


def read_log(path: Optional[Path | str] = None) -> List[Dict[str, Any]]:
    """Read all records from the score log (skip blank / corrupt lines)."""
    p = Path(path) if path else default_log_path()
    if not p.exists():
        return []
    records: List[Dict[str, Any]] = []
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
                records.append(rec)
    return records


def append_record(
    event: str,
    body: Dict[str, Any],
    *,
    path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """
    Append one hash-chained record. Returns the full record written.

    event: forecast | settlement | score
    """
    if event not in ("forecast", "settlement", "score"):
        raise ValueError("event must be forecast|settlement|score")

    p = Path(path) if path else default_log_path()
    _ensure_parent(p)

    prev_hash = _last_record_hash(p)
    logged_at = datetime.now(timezone.utc).isoformat()
    # Hash over content excluding record_hash itself
    preimage = {
        "schema": SCHEMA,
        "event": event,
        "logged_at": logged_at,
        "prev_hash": prev_hash,
        "body": body,
    }
    record_hash = _hash_payload(preimage)
    record = {**preimage, "record_hash": record_hash}

    with p.open("a", encoding="utf-8") as fh:
        fh.write(_canonical(record) + "\n")
    return record


def append_forecast(
    forecast: Dict[str, Any],
    *,
    path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    return append_record("forecast", {"forecast": forecast}, path=path)


def append_settlement(
    settlement: Dict[str, Any],
    *,
    forecast: Optional[Dict[str, Any]] = None,
    path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    body: Dict[str, Any] = {"settlement": settlement}
    if forecast is not None:
        body["forecast"] = forecast
    return append_record("settlement", body, path=path)


def append_score(
    score: Dict[str, Any],
    *,
    forecast: Optional[Dict[str, Any]] = None,
    settlement: Optional[Dict[str, Any]] = None,
    path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    body: Dict[str, Any] = {"score": score}
    if forecast is not None:
        body["forecast"] = forecast
    if settlement is not None:
        body["settlement"] = settlement
    return append_record("score", body, path=path)


def settle_and_log(
    forecast: Dict[str, Any],
    *,
    outcome_value: float,
    settlement_decision: str,
    authority_kind: str = "operator",
    authority_ref: Optional[str] = None,
    authority_note: Optional[str] = None,
    evidence_ref: Optional[str] = None,
    path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """
    Operator settlement path: settle → append settlement → score_pair → append score.

    Returns {settlement, score, settlement_record, score_record}.
    Does not invent Brier if decision is VOID/CONFLICT (score status = NOT_COMPUTABLE).
    """
    from .settlement import settle

    # Ensure forecast is present in the log so series recompute can join pairs.
    existing = index_forecasts(read_log(path))
    forecast_record = None
    fid = str(forecast.get("forecast_id") or "")
    if fid and fid not in existing:
        forecast_record = append_forecast(forecast, path=path)

    settlement = settle(
        forecast,
        outcome_value=outcome_value,
        settlement_decision=settlement_decision,
        authority_kind=authority_kind,
        authority_ref=authority_ref,
        authority_note=authority_note,
        evidence_ref=evidence_ref,
    )
    settlement_record = append_settlement(settlement, forecast=forecast, path=path)
    score = score_pair(forecast, settlement)
    score_record = append_score(score, forecast=forecast, settlement=settlement, path=path)
    return {
        "settlement": settlement,
        "score": score,
        "settlement_record": settlement_record,
        "score_record": score_record,
        "forecast_record": forecast_record,
        "scorable": is_scorable(settlement),
    }


def index_forecasts(records: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """forecast_id → latest forecast body seen in log."""
    out: Dict[str, Dict[str, Any]] = {}
    for rec in records:
        body = rec.get("body") or {}
        fc = body.get("forecast")
        if isinstance(fc, dict) and fc.get("forecast_id"):
            out[str(fc["forecast_id"])] = fc
    return out


def index_settlements(records: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """forecast_id → latest settlement body (last write wins)."""
    out: Dict[str, Dict[str, Any]] = {}
    for rec in records:
        if rec.get("event") != "settlement":
            continue
        body = rec.get("body") or {}
        st = body.get("settlement")
        if isinstance(st, dict) and st.get("forecast_id"):
            out[str(st["forecast_id"])] = st
    return out


def load_pairs(
    path: Optional[Path | str] = None,
    *,
    signal_key: Optional[str] = None,
) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """Build forecast–settlement pairs from the log for scoring."""
    records = read_log(path)
    forecasts = index_forecasts(records)
    settlements = index_settlements(records)
    pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for fid, settlement in settlements.items():
        forecast = forecasts.get(fid)
        if forecast is None:
            # settlement body may embed forecast
            continue
        if signal_key and forecast.get("signal_key") != signal_key:
            continue
        pairs.append((forecast, settlement))
    return pairs


def recompute_series(
    path: Optional[Path | str] = None,
    *,
    signal_key: Optional[str] = None,
    reference: str = "climatology",
    n_bins: int = 10,
    cohort: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Recompute score_series from the append-only log (source of truth = log)."""
    pairs = load_pairs(path, signal_key=signal_key)
    cohort_meta = {
        "log_path": str(Path(path) if path else default_log_path()),
        "signal_key": signal_key,
        "source": "score_log",
        **(cohort or {}),
    }
    return score_series(pairs, reference=reference, cohort=cohort_meta, n_bins=n_bins)


def verify_chain(path: Optional[Path | str] = None) -> Dict[str, Any]:
    """Verify hash chain integrity of the score log."""
    records = read_log(path)
    if not records:
        return {"ok": True, "n": 0, "broken_at": None}

    expected_prev = GENESIS_HASH
    for i, rec in enumerate(records):
        if rec.get("prev_hash") != expected_prev:
            return {
                "ok": False,
                "n": len(records),
                "broken_at": i,
                "reason": "prev_hash mismatch",
                "expected_prev": expected_prev,
                "actual_prev": rec.get("prev_hash"),
            }
        preimage = {
            "schema": rec.get("schema"),
            "event": rec.get("event"),
            "logged_at": rec.get("logged_at"),
            "prev_hash": rec.get("prev_hash"),
            "body": rec.get("body"),
        }
        computed = _hash_payload(preimage)
        if computed != rec.get("record_hash"):
            return {
                "ok": False,
                "n": len(records),
                "broken_at": i,
                "reason": "record_hash mismatch",
                "expected": computed,
                "actual": rec.get("record_hash"),
            }
        expected_prev = rec["record_hash"]

    return {"ok": True, "n": len(records), "tip_hash": expected_prev, "broken_at": None}
