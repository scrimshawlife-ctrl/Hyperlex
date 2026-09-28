"""The SELECT-005 harvest stops before fetch when the exposure snapshot is stale."""

import hashlib
from pathlib import Path

import pytest

from hyperlexical.eval_routing import procedure_hash
from hyperlexical.select_005_harvest import STALE, exposure_fence
from hyperlexical.select_005_reserve import canonical_json

REPO = Path(__file__).resolve().parents[2]
ROUTING_SPEC = "002e2ac67e5ee00c27ecedd4566b9e7d900852c51e3ac57aac957ac095899d96"
ROUTING_SCHEMA = "147e2787e6e66ba47acd185fa6602a10bd5d57c15ea446f574b2e750277d31a0"
PROCEDURE = "ad187d262eba280dd4b88d2204e03d4dfb255f9b0fb443bd250a0e441a7ea6db"


def _pair(age_seconds: float) -> dict:
    compared = "1790631188.652030"
    mtime = f"{float(compared) - age_seconds:.6f}"
    return exposure_fence(
        [
            {
                "kind": "vern",
                "mtime_unix": mtime,
                "path": "inbox/vern-texts-example.jsonl",
                "sha256": "ab" * 32,
                "snapshot_id": "example",
            },
            {
                "kind": "boxhash",
                "mtime_unix": mtime,
                "path": "inbox/box-jev-hashes-example.txt",
                "sha256": "cd" * 32,
                "snapshot_id": "example",
            },
        ],
        compared_at_unix=compared,
    )


def test_stale_snapshot_stops_before_fetch_and_is_deterministic():
    first = _pair(72.32 * 3600)
    second = _pair(72.32 * 3600)
    assert first["state"] == STALE
    assert first["fetch_authorized"] is False
    assert first["harvest_executed"] is False
    assert first["network_requests"] == 0
    assert first["rows_acquired"] == 0
    assert first["exposure_fence_bypassed"] is False
    assert first["stop_before"] == "source_fetch"
    assert float(first["worst_age_hours"]) > 6
    assert canonical_json(first) == canonical_json(second)


def test_fresh_fence_does_not_fetch():
    record = _pair(3600)
    assert record["state"] == "EXPOSURE_SNAPSHOT_FRESH"
    assert record["fetch_authorized"] is True
    assert record["harvest_executed"] is False
    assert record["network_requests"] == 0
    assert record["rows_acquired"] == 0
    assert record["stop_before"] is None


def test_missing_snapshot_kind_is_stale():
    record = exposure_fence(
        [
            {
                "kind": "vern",
                "mtime_unix": "1790630000.000000",
                "path": "inbox/vern-only.jsonl",
                "sha256": "ef" * 32,
                "snapshot_id": "partial",
            }
        ],
        compared_at_unix="1790631000.000000",
    )
    assert record["state"] == STALE
    assert record["missing_kinds"] == ["boxhash"]
    assert record["fetch_authorized"] is False


def test_widening_the_fence_is_refused():
    with pytest.raises(SystemExit, match="cannot be widened"):
        exposure_fence([], compared_at_unix="1.0", limit_h=7)


def test_harvester_module_has_no_fetch_client():
    text = (REPO / "scripts/shadow/hyperlexical/select_005_harvest.py").read_text()
    for banned in ("urllib", "import requests", "httpx", "import socket", "hs_run", "urlopen"):
        assert banned not in text


def test_routing_contract_bytes_stay_frozen():
    spec = REPO / "specs/007-hyperlexical-model/select-eval-routing-contract.md"
    schema = (
        REPO
        / "specs/007-hyperlexical-model/schemas/hyperlex/select/eval-routing.schema.json"
    )
    assert hashlib.sha256(spec.read_bytes()).hexdigest() == ROUTING_SPEC
    assert hashlib.sha256(schema.read_bytes()).hexdigest() == ROUTING_SCHEMA
    assert procedure_hash() == PROCEDURE
