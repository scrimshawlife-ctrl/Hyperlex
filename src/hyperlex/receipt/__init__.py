"""receipt — archive_of_becoming (Numogram Zone 0 + results_metric).

Canonical receipt emission with integrity + schema validation support.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Tuple

from ..schemas import validate_receipt


def _canonical_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def emit_receipt(result: dict, out_dir: str | Path | None = None, validate: bool = False) -> Path:
    """Emit a timestamped canonical receipt for the memetic scan."""
    if out_dir is None:
        out_dir = Path.home() / ".hyperlex" / "receipts"
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    ts = result.get("provenance", {}).get("timestamp", "now").replace(":", "").replace("-", "").split(".")[0][:15]
    path = out / f"hyperlex_{ts}.json"

    canonical = _canonical_json(result)
    receipt = dict(result)
    receipt["receipt"] = {
        "path": str(path),
        "integrity": hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12],
    }

    if validate:
        ok, msg = validate_receipt(receipt)
        receipt["receipt"]["schema_validation"] = {"valid": ok, "message": msg}

    with path.open("w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2, sort_keys=True)
    return path


def verify_receipt(payload: dict) -> Tuple[bool, str]:
    """Verify receipt integrity in-memory."""
    if not isinstance(payload, dict):
        return False, "payload must be object"
    receipt = payload.get("receipt")
    if not isinstance(receipt, dict):
        return False, "missing receipt block"
    expected = str(receipt.get("integrity", "")).strip()
    if not expected:
        return False, "missing receipt.integrity"
    canonical = _canonical_json({k: v for k, v in payload.items() if k != "receipt"})
    actual = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]
    if actual != expected:
        return False, f"integrity mismatch: expected {expected}, actual {actual}"
    return True, "valid"
