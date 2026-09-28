"""Exposure refresh does not invent a snapshot or start a harvest."""

import hashlib
from pathlib import Path

from hyperlexical.select_005_exposure_refresh import (
    PREVIOUS_SNAPSHOT_ID,
    UNAVAILABLE,
    pair_binding,
    workflow_gate,
)
from hyperlexical.select_005_harvest import STALE

REPO = Path(__file__).resolve().parents[2]
HARVEST_SHA256 = "8f58f30ca85af2e476064c7afea9498b02a53d71c4890d38b4cdc2baaf83021c"


def _obs(**overrides):
    base = {
        "executable_present": False,
        "host": "spark-bf46",
        "snapshot_only_entrypoint_present": False,
        "vernacular_source_present": False,
    }
    base.update(overrides)
    return base


def _pair(snapshot_id: str, age_seconds: float, *, vern_id: str | None = None, box_id: str | None = None):
    compared = "1790631188.652030"
    mtime = f"{float(compared) - age_seconds:.6f}"
    vern_snapshot = vern_id or snapshot_id
    box_snapshot = box_id or snapshot_id
    return [
        {
            "kind": "vern",
            "mtime_unix": mtime,
            "path": f"inbox/vern-texts-{vern_snapshot}.jsonl",
            "sha256": "ab" * 32,
            "snapshot_id": vern_snapshot,
        },
        {
            "kind": "boxhash",
            "mtime_unix": mtime,
            "path": f"inbox/box-jev-hashes-{box_snapshot}.txt",
            "sha256": "cd" * 32,
            "snapshot_id": box_snapshot,
        },
    ], compared


def test_missing_workflow_stops_without_a_snapshot_or_harvest():
    record = workflow_gate(_obs())
    assert record["state"] == UNAVAILABLE
    assert record["snapshot_id"] is None
    assert record["harvest_run"] is False
    assert record["reserve_recensus_run"] is False
    assert record["training_run"] is False
    assert record["network_requests"] == 0
    assert record["previous_pair_overwritten"] is False
    assert record["previous_pair_reused"] is False
    assert record["previous_snapshot_id"] == PREVIOUS_SNAPSHOT_ID
    assert record["missing"]


def test_a_daily_script_that_also_harvests_is_not_a_snapshot_entrypoint():
    record = workflow_gate(
        _obs(
            host="box",
            executable_present=True,
            vernacular_source_present=True,
            snapshot_only_entrypoint_present=False,
        )
    )
    assert record["state"] == UNAVAILABLE
    assert record["harvest_run"] is False
    assert any("hs_run.py run" in item for item in record["missing"])


def test_matching_fresh_ids_bind_and_a_mismatch_or_stale_pair_does_not_pass():
    fresh, compared = _pair("20260928T220000Z", 3600)
    bound = pair_binding(fresh, compared_at_unix=compared)
    assert bound["pair_binding_status"] == "BOUND"
    assert bound["structural_validation"] == "PASS"
    assert bound["vern_snapshot_id"] == bound["box_snapshot_id"] == "20260928T220000Z"
    assert bound["freshness_result"] == "EXPOSURE_SNAPSHOT_FRESH"
    assert float(bound["binding_age_hours"]) <= 6
    assert bound["harvest_run"] is False

    mismatched, compared = _pair(
        "20260928T220000Z",
        3600,
        box_id="20260928T220100Z",
    )
    refused = pair_binding(mismatched, compared_at_unix=compared)
    assert refused["pair_binding_status"] == "MISMATCHED"
    assert refused["structural_validation"] == "FAIL"
    assert refused["state"] == "EXPOSURE_SNAPSHOT_INVALID"
    assert refused["freshness_result"] is None

    stale, compared = _pair("20260925T211351Z", 72.32 * 3600)
    old = pair_binding(stale, compared_at_unix=compared)
    assert old["state"] == STALE
    assert old["freshness_result"] == STALE
    assert float(old["binding_age_hours"]) > 6


def test_refresh_module_does_not_invoke_harvest_and_harvest_file_is_unchanged():
    text = (REPO / "scripts/shadow/hyperlexical/select_005_exposure_refresh.py").read_text()
    for banned in ("subprocess", "urllib", "urlopen", "import hs_run", "Popen"):
        assert banned not in text
    harvest = REPO / "scripts/shadow/hyperlexical/select_005_harvest.py"
    assert hashlib.sha256(harvest.read_bytes()).hexdigest() == HARVEST_SHA256
