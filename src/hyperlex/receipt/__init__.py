"""receipt — archive_of_becoming (Numogram Zone 0 + results_metric).

Canonical receipt emission with integrity + schema validation support.
Optional append-only receipt ledger (hash-chained index).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional, Tuple

from ..guards import receipt_legacy_integrity_enabled
from ..schemas import validate_receipt
from .ledger import (
    append_receipt_index,
    default_ledger_path,
    list_receipts,
    read_ledger,
    verify_ledger_chain,
)
from .stats import ledger_stats


def _canonical_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def emit_receipt(
    result: dict,
    out_dir: str | Path | None = None,
    validate: bool = True,
    *,
    append_ledger: bool = True,
    ledger_path: str | Path | None = None,
) -> Path:
    """Emit a timestamped canonical receipt for the memetic scan.

    When append_ledger=True (default), also append a hash-chained index entry
    to the receipt ledger (~/.hyperlex/receipt_ledger.jsonl).
    """
    if out_dir is None:
        out_dir = Path.home() / ".hyperlex" / "receipts"
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    canonical = _canonical_json(result)
    integrity = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    ts = result.get("provenance", {}).get("timestamp", "now").replace(":", "").replace("-", "").split(".")[0][:15]
    # short filename suffix; receipt.integrity remains the full 64-char digest
    path = out / f"hyperlex_{ts}_{integrity[:12]}.json"

    receipt = dict(result)
    receipt["receipt"] = {
        "path": str(path),
        "integrity": integrity,
    }

    if validate:
        ok, msg = validate_receipt(receipt)
        receipt["receipt"]["schema_validation"] = {"valid": ok, "message": msg}

    with path.open("w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2, sort_keys=True)

    if append_ledger:
        try:
            entry = append_receipt_index(
                receipt,
                receipt_path=path,
                path=ledger_path,
            )
            receipt["receipt"]["ledger_record_hash"] = entry.get("record_hash")
            # rewrite with ledger pointer (integrity already covers body without this key —
            # only store pointer outside hashed body via side file is cleaner; keep as
            # non-canonical metadata on disk after write is OK for operators).
            with path.open("w", encoding="utf-8") as f:
                json.dump(receipt, f, indent=2, sort_keys=True)
        except ValueError:
            # fail-open on ledger only if integrity missing (should not happen)
            pass

    # Fail-open: index receipt into configured vector backend (sqlite or local chroma)
    try:
        from ..vectordb.autoindex import index_receipt_path

        index_receipt_path(path)
    except Exception:
        pass

    return path


def verify_receipt(payload: dict) -> Tuple[bool, str]:
    """Verify receipt integrity in-memory.

    Integrity is over all fields except the top-level ``receipt`` block,
    so ledger_record_hash inside receipt does not affect the hash.
    """
    if not isinstance(payload, dict):
        return False, "payload must be object"
    receipt = payload.get("receipt")
    if not isinstance(receipt, dict):
        return False, "missing receipt block"
    expected = str(receipt.get("integrity", "")).strip()
    if not expected:
        return False, "missing receipt.integrity"
    canonical = _canonical_json({k: v for k, v in payload.items() if k != "receipt"})
    actual_full = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if expected == actual_full:
        return True, "valid"
    if (
        len(expected) == 12
        and expected == actual_full[:12]
        and receipt_legacy_integrity_enabled()
    ):
        return True, "valid (legacy 12-char; HYPERLEX_RECEIPT_LEGACY_INTEGRITY=1)"
    return False, f"integrity mismatch: expected {expected}, actual {actual_full}"


__all__ = [
    "emit_receipt",
    "verify_receipt",
    "append_receipt_index",
    "default_ledger_path",
    "list_receipts",
    "read_ledger",
    "verify_ledger_chain",
    "ledger_stats",
]
