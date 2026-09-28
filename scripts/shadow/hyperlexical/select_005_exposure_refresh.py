"""SELECT-005 exposure refresh stops when the box-side generator is absent.

The canonical command is ``heldout-stream-daily`` on the box. It is not on
this host, and its documented second step is ``hs_run.py run``. A Notion
term/event census is not a substitute for that command. This module does not
generate exposure rows, does not copy an old snapshot forward, and does not
harvest.
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
NOTION_NOT_JEV_HASH_LIST = (
    "notion term and event registries are not the jev-lane hash list"
)
_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z$")
_VERN = re.compile(r"^vern-texts-([0-9]{8}T[0-9]{6}Z)\.jsonl$")
_BOX = re.compile(r"^box-jev-hashes-([0-9]{8}T[0-9]{6}Z)\.txt$")
_LANE_FLAGS = (
    "candidates_database_present",
    "discovery_lane_export_present",
    "jev_lane_hash_generator_present",
    "observations_database_present",
    "obsidian_export_present",
)


def workflow_gate(observation: Mapping[str, Any]) -> dict[str, Any]:
    """Classify whether a canonical snapshot-only generator can be run.

    A present daily script is not enough: the documented command also starts
    ``hs_run.py run``. Notion term and event rows do not supply the box hash
    list. This function never executes either step.
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
    source_kind = str(observation.get("vernacular_source_kind") or "")
    if source_kind == "notion":
        if observation.get("jev_lane_hash_generator_present") is not True:
            missing.append(NOTION_NOT_JEV_HASH_LIST)
    elif observation.get("vernacular_source_present") is not True:
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


def notion_registry_gap(census: Mapping[str, Any]) -> dict[str, Any]:
    """Refuse a pair built from Notion term and event counts alone.

    The box hash list is the over-inclusive Jev-lane exposure set. Term and
    event registries are a different object. This function does not read
    Notion and does not write snapshot bytes.
    """
    terms = census.get("terms")
    events = census.get("events")
    counted = (
        isinstance(terms, int)
        and not isinstance(terms, bool)
        and isinstance(events, int)
        and not isinstance(events, bool)
        and terms >= 0
        and events >= 0
    )
    missing = []
    if not counted:
        missing.append("notion census is incomplete")
    if census.get("candidates_database_present") is not True:
        missing.append("notion has no candidates database")
    if census.get("observations_database_present") is not True:
        missing.append("notion has no observations database")
    if census.get("discovery_lane_export_present") is not True:
        missing.append("discovery lane export is absent")
    if census.get("obsidian_export_present") is not True:
        missing.append("obsidian export is absent")
    if census.get("jev_lane_hash_generator_present") is not True:
        missing.append(NOTION_NOT_JEV_HASH_LIST)
    lanes_present = all(census.get(key) is True for key in _LANE_FLAGS)
    return {
        "events": events if counted else None,
        "harvest_run": False,
        "missing": missing,
        "network_requests": 0,
        "pair_written": False,
        "previous_pair_overwritten": False,
        "previous_pair_reused": False,
        "snapshot_id": None,
        "state": UNAVAILABLE if missing or not lanes_present else "EXPOSURE_REFRESH_NOT_RUN",
        "terms": terms if counted else None,
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
