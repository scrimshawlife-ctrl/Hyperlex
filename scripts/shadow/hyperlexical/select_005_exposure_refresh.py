"""SELECT-005 exposure refresh stops when the box-side generator is absent.

The canonical command is ``heldout-stream-daily`` on the box. It is not on
this host, and its documented second step is ``hs_run.py run``. This module
does not generate exposure rows, does not copy an old snapshot forward, and
does not harvest.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from .select_005_harvest import STALE, exposure_fence
from .select_005_reserve import EXPERIMENT_ID

TRANSITION = "SELECT_005_EXPOSURE_SNAPSHOT_REFRESH_AUTHORIZATION"
UNAVAILABLE = "EXPOSURE_REFRESH_WORKFLOW_UNAVAILABLE"
INVALID = "EXPOSURE_SNAPSHOT_INVALID"
CANONICAL_PROCEDURE = (
    "/workspace/deliverables/hyperlex-heldout-stream/bin/heldout-stream-daily"
)
CANONICAL_HOST = "box"
PREVIOUS_SNAPSHOT_ID = "20260925T211351Z"
_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z$")
_VERN = re.compile(r"^vern-texts-([0-9]{8}T[0-9]{6}Z)\.jsonl$")
_BOX = re.compile(r"^box-jev-hashes-([0-9]{8}T[0-9]{6}Z)\.txt$")


def workflow_gate(observation: Mapping[str, Any]) -> dict[str, Any]:
    """Classify whether a canonical snapshot-only generator can be run.

    A present daily script is not enough: the documented command also starts
    ``hs_run.py run``. This function never executes either step.
    """
    missing = []
    if str(observation.get("host") or "") != CANONICAL_HOST:
        missing.append("procedure host is not the box")
    if observation.get("executable_present") is not True:
        missing.append("heldout-stream-daily is absent")
    if observation.get("snapshot_only_entrypoint_present") is not True:
        missing.append(
            "no snapshot-only entrypoint; the documented command also runs hs_run.py run"
        )
    if observation.get("vernacular_source_present") is not True:
        missing.append("vernacular sqlite source is absent")
    unavailable = bool(missing)
    return {
        "canonical_host": CANONICAL_HOST,
        "canonical_procedure": CANONICAL_PROCEDURE,
        "experiment_id": EXPERIMENT_ID,
        "harvest_run": False,
        "missing": missing,
        "network_requests": 0,
        "previous_pair_overwritten": False,
        "previous_pair_reused": False,
        "previous_snapshot_id": PREVIOUS_SNAPSHOT_ID,
        "reserve_recensus_run": False,
        "snapshot_id": None,
        "state": UNAVAILABLE if unavailable else "EXPOSURE_REFRESH_NOT_RUN",
        "training_run": False,
        "transition": TRANSITION,
    }


def _name_id(path: str, pattern: re.Pattern[str]) -> str | None:
    name = path.rstrip("/").split("/")[-1]
    found = pattern.fullmatch(name)
    if found is None:
        return None
    snapshot_id = found.group(1)
    if _ID.fullmatch(snapshot_id) is None:
        return None
    return snapshot_id


def pair_binding(
    snapshots: Sequence[Mapping[str, Any]],
    *,
    compared_at_unix: str,
) -> dict[str, Any]:
    """Bind a Vern file to a box-hash file. Does not read or write their bytes.

    Age uses ``exposure_fence``, the same formula as the harvest stop.
    """
    by_kind = {str(item.get("kind") or ""): item for item in snapshots}
    vern_id = _name_id(str(by_kind.get("vern", {}).get("path") or ""), _VERN)
    box_id = _name_id(str(by_kind.get("boxhash", {}).get("path") or ""), _BOX)
    declared = {str(item.get("snapshot_id") or "") for item in snapshots}
    ids_match = (
        vern_id is not None
        and vern_id == box_id
        and declared == {vern_id}
    )
    if not ids_match:
        return {
            "binding_age_hours": None,
            "box_snapshot_id": box_id,
            "freshness_result": None,
            "harvest_run": False,
            "pair_binding_status": "MISMATCHED",
            "state": INVALID,
            "structural_validation": "FAIL",
            "vern_snapshot_id": vern_id,
        }
    fence = exposure_fence(snapshots, compared_at_unix=compared_at_unix)
    structural = "PASS" if not fence["missing_kinds"] else "FAIL"
    state = fence["state"] if structural == "PASS" else INVALID
    return {
        "binding_age_hours": fence["worst_age_hours"],
        "box_age_hours": next(
            row["age_hours"] for row in fence["snapshots"] if row["kind"] == "boxhash"
        ),
        "box_snapshot_id": box_id,
        "comparison_timestamp_unix": str(compared_at_unix),
        "freshness_limit_hours": fence["limit_hours"],
        "freshness_result": state,
        "harvest_run": False,
        "pair_binding_status": "BOUND" if structural == "PASS" else "INCOMPLETE",
        "state": state,
        "structural_validation": structural,
        "vern_age_hours": next(
            row["age_hours"] for row in fence["snapshots"] if row["kind"] == "vern"
        ),
        "vern_snapshot_id": vern_id,
    }
