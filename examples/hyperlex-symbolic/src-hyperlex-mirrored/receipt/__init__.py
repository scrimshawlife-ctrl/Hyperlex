"""receipt — archive_of_becoming (Numogram Zone 0 + results_metric)

Canonical receipt emission with integrity.
"""
from pathlib import Path as _Path
import json

def emit_receipt(result: dict, out_dir: str | None = None) -> "Path":
    """Emit a timestamped canonical receipt for the memetic scan."""
    if out_dir is None:
        out_dir = _Path.home() / ".hyperlex" / "receipts"
    out = _Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    ts = result.get("provenance", {}).get("timestamp", "now").replace(":", "").replace("-", "").split(".")[0][:15]
    path = out / f"hyperlex_{ts}.json"

    canonical = json.dumps(result, sort_keys=True, separators=(",", ":"))
    receipt = dict(result)
    receipt["receipt"] = {
        "path": str(path),
        "integrity": __import__("hashlib").sha256(canonical.encode()).hexdigest()[:12]
    }
    with open(path, "w") as f:
        json.dump(receipt, f, indent=2)
    return path
