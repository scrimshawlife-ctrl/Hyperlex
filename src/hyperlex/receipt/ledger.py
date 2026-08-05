"""Append-only, hash-chained receipt ledger.

Default: ~/.hyperlex/receipt_ledger.jsonl
Override: HYPERLEX_RECEIPT_LEDGER env, or explicit path.

Each line is a lightweight index entry (not the full receipt body):
path, integrity, canonical_hash, timestamp, query, lineage_family, prev_hash, record_hash.

Full receipt JSON remains the primary artifact on disk; the ledger is the
auditable index + chain.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA = "hyperlex.receipt_ledger.v1"
GENESIS_HASH = "0" * 64
DEFAULT_NAME = "receipt_ledger.jsonl"


def default_ledger_path() -> Path:
    env = os.environ.get("HYPERLEX_RECEIPT_LEDGER", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / ".hyperlex" / DEFAULT_NAME).resolve()


def _canonical(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash_payload(obj: Dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


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


def read_ledger(path: Optional[Path | str] = None) -> List[Dict[str, Any]]:
    p = Path(path) if path else default_ledger_path()
    if not p.exists():
        return []
    out: List[Dict[str, Any]] = []
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
                out.append(rec)
    return out


def append_receipt_index(
    receipt: Dict[str, Any],
    *,
    receipt_path: str | Path,
    path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """
    Append a ledger index entry for an emitted receipt.

    Requires receipt['receipt']['integrity']. Fail-closed if missing.
    """
    block = receipt.get("receipt") if isinstance(receipt, dict) else None
    if not isinstance(block, dict) or not block.get("integrity"):
        raise ValueError("receipt.integrity required for ledger append")

    prov = receipt.get("provenance") or {}
    analysis = receipt.get("analysis") or {}
    lineage = analysis.get("lineage") or {}

    p = Path(path) if path else default_ledger_path()
    p.parent.mkdir(parents=True, exist_ok=True)

    prev_hash = _last_record_hash(p)
    logged_at = datetime.now(timezone.utc).isoformat()
    body = {
        "receipt_path": str(receipt_path),
        "integrity": str(block["integrity"]),
        "canonical_hash": prov.get("canonical_hash"),
        "timestamp": prov.get("timestamp"),
        "version": prov.get("version"),
        "ingest_source": prov.get("ingest_source"),
        "query": None,
        "lineage_family": lineage.get("family_id"),
        "lineage_confidence": lineage.get("confidence"),
        "hyperstition_risk": prov.get("hyperstition_risk"),
        "brier": prov.get("brier"),  # should be null on open analysis
    }
    # best-effort query from notes or observed prefix
    if isinstance(receipt.get("observed"), str):
        body["observed_preview"] = receipt["observed"][:160]

    preimage = {
        "schema": SCHEMA,
        "event": "receipt",
        "logged_at": logged_at,
        "prev_hash": prev_hash,
        "body": body,
    }
    record_hash = _hash_payload(preimage)
    record = {**preimage, "record_hash": record_hash}

    with p.open("a", encoding="utf-8") as fh:
        fh.write(_canonical(record) + "\n")
    return record


def verify_ledger_chain(path: Optional[Path | str] = None) -> Dict[str, Any]:
    records = read_ledger(path)
    if not records:
        return {"ok": True, "n": 0, "broken_at": None, "tip_hash": GENESIS_HASH}

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


def list_receipts(
    path: Optional[Path | str] = None,
    *,
    limit: int = 50,
    lineage_family: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return recent ledger entries (newest last by default; slice from end)."""
    records = read_ledger(path)
    bodies: List[Dict[str, Any]] = []
    for rec in records:
        body = dict(rec.get("body") or {})
        body["logged_at"] = rec.get("logged_at")
        body["record_hash"] = rec.get("record_hash")
        if lineage_family and body.get("lineage_family") != lineage_family:
            continue
        bodies.append(body)
    if limit and limit > 0:
        return bodies[-limit:]
    return bodies
