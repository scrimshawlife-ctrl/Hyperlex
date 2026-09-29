"""SELECT-005 harvest authorization stops when the exposure snapshot is stale.

This module does not fetch, harvest, settle, recensus, or train.
It does not modify the routing contract. A fresh fence is permission to
start a later harvest. It is not a harvest.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .select_005_completion import BOX_SNAPSHOT_LIMIT_H
from .select_005_reserve import EXPERIMENT_ID, canonical_json, sha256_text

TRANSITION = "SELECT_005_FRESH_SOURCE_HARVEST_AND_ROUTING_AUTHORIZATION"
STALE = "EXPOSURE_SNAPSHOT_STALE"
FRESH = "EXPOSURE_SNAPSHOT_FRESH"
REQUIRED_KINDS = ("vern", "boxhash")


def exposure_fence(
    snapshots: Sequence[Mapping[str, Any]],
    *,
    compared_at_unix: str,
    limit_h: float = BOX_SNAPSHOT_LIMIT_H,
) -> dict[str, Any]:
    """Return the exposure decision for one frozen snapshot pair.

    Ages are ``compared_at_unix`` minus each ``mtime_unix``. Both values are
    decimal strings, so the record does not read a clock and does not fetch.
    """
    if float(limit_h) > BOX_SNAPSHOT_LIMIT_H:
        raise SystemExit("REFUSE: exposure fence cannot be widened")
    rows = []
    for item in snapshots:
        mtime = str(item.get("mtime_unix") or "")
        age_h = (float(compared_at_unix) - float(mtime)) / 3600.0
        rows.append(
            {
                "age_hours": f"{age_h:.6f}",
                "kind": str(item.get("kind") or ""),
                "mtime_unix": mtime,
                "path": str(item.get("path") or ""),
                "sha256": str(item.get("sha256") or ""),
                "snapshot_id": str(item.get("snapshot_id") or ""),
            }
        )
    rows.sort(key=lambda row: (row["kind"], row["snapshot_id"], row["path"]))
    present = {row["kind"] for row in rows}
    missing = [kind for kind in REQUIRED_KINDS if kind not in present]
    worst = max((row["age_hours"] for row in rows), default=None)
    stale = bool(missing) or worst is None or float(worst) > float(limit_h)
    binding = None
    if rows:
        binding = max(rows, key=lambda row: (float(row["age_hours"]), row["kind"]))
    record = {
        "binding_snapshot": binding,
        "compared_at_unix": str(compared_at_unix),
        "experiment_id": EXPERIMENT_ID,
        "exposure_fence_bypassed": False,
        "fetch_authorized": not stale,
        "harvest_executed": False,
        "limit_hours": f"{float(limit_h):.1f}",
        "missing_kinds": missing,
        "network_requests": 0,
        "rows_acquired": 0,
        "snapshots": rows,
        "state": STALE if stale else FRESH,
        "stop_before": "source_fetch" if stale else None,
        "transition": TRANSITION,
        "worst_age_hours": worst,
    }
    body = {key: value for key, value in record.items() if key != "record_sha256"}
    record["record_sha256"] = sha256_text(canonical_json(body))
    return record
