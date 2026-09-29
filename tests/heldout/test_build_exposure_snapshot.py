"""The exposure successor is a superset of the historical pair and does not harvest."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from build_exposure_snapshot import (
    ABSENT_BY_DEFAULT,
    MONOTONICITY_FAILURE,
    PLANNED,
    RECONSTRUCTED,
    assess_monotonicity,
    build_receipt,
    main,
    plan_reconstruction,
    publish_pair,
)


def _box(*digests: str) -> str:
    return "".join(item + "\n" for item in digests)


def _vern(*values: str) -> str:
    return "".join(json.dumps(value) + "\n" for value in values)


def _plan(box: str, vern: str, **kwargs):
    return plan_reconstruction(
        baseline_box_text=box,
        baseline_vern_text=vern,
        baseline_snapshot_id="20260925T211351Z",
        baseline_box_sha256="ab" * 32,
        baseline_vern_sha256="cd" * 32,
        absent_families=ABSENT_BY_DEFAULT,
        **kwargs,
    )


def test_successor_keeps_every_historical_hash_and_adds_only_new_ones() -> None:
    old = "a" * 64
    extra = "b" * 64
    plan = _plan(
        _box(old),
        _vern("kept"),
        box_increments=(
            {
                "artifact": "agent-context-exposed-normtext-sha256.txt",
                "family": "agent_context_exposed_hashes",
                "source_sha256": "ef" * 32,
                "text": _box(old, extra),
            },
        ),
    )
    assert plan["monotonicity"]["ok"] is True
    assert plan["box_added"] == 1
    assert plan["box_count"] == 2
    assert extra in plan["box_text"]
    assert old in plan["box_text"]
    assert plan["vern_bytes_carried_forward"] is True
    assert plan["vern_added"] == 0
    receipt = build_receipt(plan, snapshot_id=None, published=False, fence=None)
    assert receipt["state"] == PLANNED
    assert receipt["harvest_run"] is False
    assert receipt["training_authorized"] is False
    assert "notion_not_a_box_hash_source" in receipt["absent_families"]


def test_a_dropped_historical_hash_is_not_publishable() -> None:
    previous = {"a" * 64, "b" * 64}
    successor = {"b" * 64}
    assessment = assess_monotonicity(previous, successor, {"kept"}, {"kept"})
    assert assessment["ok"] is False
    assert assessment["box_missing"] == 1
    plan = _plan(_box("a" * 64), _vern("kept"))
    plan["monotonicity"] = assessment
    receipt = build_receipt(plan, snapshot_id=None, published=False, fence=None)
    assert receipt["state"] == MONOTONICITY_FAILURE
    with pytest.raises(SystemExit, match="cannot be published"):
        build_receipt(plan, snapshot_id="20260929T000000Z", published=True, fence=None)


def test_notion_titles_are_refused_as_snapshot_sources() -> None:
    with pytest.raises(SystemExit, match="notion"):
        _plan(
            _box("a" * 64),
            _vern("kept"),
            box_increments=(
                {
                    "artifact": "notion",
                    "family": "notion",
                    "source_sha256": "11" * 32,
                    "text": _box("c" * 64),
                },
            ),
        )


def test_publish_writes_both_names_and_refuses_a_second_copy(tmp_path: Path) -> None:
    plan = _plan(_box("d" * 64), _vern("kept\nline"))
    snapshot_id = "20260929T010203Z"
    vern_path, box_path = publish_pair(tmp_path, snapshot_id, plan["box_text"], plan["vern_text"])
    assert vern_path.name == f"vern-texts-{snapshot_id}.jsonl"
    assert box_path.name == f"box-jev-hashes-{snapshot_id}.txt"
    assert oct(vern_path.stat().st_mode & 0o777) == "0o600"
    assert oct(box_path.stat().st_mode & 0o777) == "0o600"
    assert "20260925T211351Z" not in vern_path.name
    with pytest.raises(SystemExit, match="already published"):
        publish_pair(tmp_path, snapshot_id, plan["box_text"], plan["vern_text"])


def test_new_vern_strings_are_appended_without_rewriting_history() -> None:
    historical = json.dumps("kept", ensure_ascii=False) + "\n"
    plan = _plan(
        _box("e" * 64),
        historical,
        vern_increments=(
            {
                "artifact": "lane",
                "family": "observed_vernacular",
                "source_sha256": "22" * 32,
                "text": _vern("added"),
            },
        ),
    )
    assert plan["vern_text"].splitlines() == [json.dumps("kept"), json.dumps("added")]
    assert plan["vern_added"] == 1
    assert plan["vern_bytes_carried_forward"] is False


def test_module_does_not_fetch_or_harvest() -> None:
    source = Path(__file__).resolve().parents[2] / "scripts/heldout/build_exposure_snapshot.py"
    module = source.read_text(encoding="utf-8")
    for banned in ("subprocess", "urllib", "urlopen", "import hs_run", "Popen", "httpx"):
        assert banned not in module
    assert "does not harvest" in module


def test_cli_publish_is_fresh_and_leaves_the_baseline(tmp_path: Path) -> None:
    baseline_box = tmp_path / "box-jev-hashes-20260925T211351Z.txt"
    baseline_vern = tmp_path / "vern-texts-20260925T211351Z.jsonl"
    extra = tmp_path / "extra.txt"
    baseline_box.write_text(_box("a" * 64), encoding="utf-8")
    baseline_vern.write_text(_vern("kept"), encoding="utf-8")
    extra.write_text(_box("f" * 64), encoding="utf-8")
    before_box = baseline_box.read_bytes()
    before_vern = baseline_vern.read_bytes()
    receipt_path = tmp_path / "receipt.json"
    code = main(
        [
            "--baseline-box",
            str(baseline_box),
            "--baseline-vern",
            str(baseline_vern),
            "--box-increment",
            f"agent_context_exposed_hashes:{extra}",
            "--out-dir",
            str(tmp_path),
            "--snapshot-id",
            "20260929T020304Z",
            "--receipt",
            str(receipt_path),
            "--publish",
        ]
    )
    assert code == 0
    assert baseline_box.read_bytes() == before_box
    assert baseline_vern.read_bytes() == before_vern
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["state"] == RECONSTRUCTED
    assert receipt["published"] is True
    assert receipt["harvest_run"] is False
    assert receipt["box_added"] == 1
    assert receipt["freshness"]["state"] == "EXPOSURE_SNAPSHOT_FRESH"
    assert receipt["previous_pair_overwritten"] is False
    assert os.stat(receipt_path).st_mode & 0o777 == 0o600
