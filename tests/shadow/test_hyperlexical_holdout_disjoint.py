"""Pinned training rows and a controlled holdout must be disjoint."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.heldout_census import normalize_group_text  # noqa: E402
from hyperlexical.holdout_eligibility import census, exclusion_reason  # noqa: E402
from hyperlexical.holdout_guard import (  # noqa: E402
    assert_pinned_holdout_disjoint,
    filter_holdout_rows,
    load_holdout_spec,
    normalized_text_sha256,
    require_holdout_for_training,
)
from hyperlexical.preflight import main as preflight_main  # noqa: E402
from hyperlexical.selection_surface import row_id  # noqa: E402
from hyperlexical.train_input import load_training_bundle  # noqa: E402


def _row(text, *, split="train", task="classify", cls="OBSERVED", lineage="brainrot"):
    return {
        "text": text,
        "fillers": ["atom"],
        "roles": ["pos_0"],
        "role_scheme": "positional",
        "class": cls,
        "split": split,
        "task": task,
        "lineage": lineage,
    }


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_pin(path: Path, rows: list[dict]) -> str:
    payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.write_text(payload, encoding="utf-8")
    return _sha(path)


def _manifest(path: Path, rows: list[dict], *, experiment_id: str = "HLX-EXP-TEST") -> Path:
    path.write_text(
        json.dumps(
            {
                "schema": "hyperlex.holdout_manifest.v1",
                "status": "UNSCORED_SEALED",
                "experiment_id": experiment_id,
                "row_ids": [row_id(row) for row in rows],
                "normalized_text_sha256": [normalized_text_sha256(row["text"]) for row in rows],
            }
        ),
        encoding="utf-8",
    )
    return path


def _arm(monkeypatch, tmp_path: Path, rows: list[dict], manifest: Path) -> None:
    pinned = tmp_path / "pinned.jsonl"
    digest = _write_pin(pinned, rows)
    monkeypatch.setenv("HLX_EXPERIMENT_ID", "HLX-EXP-TEST")
    monkeypatch.setenv("HLX_TRAIN_EXPORT_PATH", str(pinned))
    monkeypatch.setenv("HLX_TRAIN_EXPORT_SHA256", digest)
    monkeypatch.setenv("HLX_TRAIN_EXPORT_ROWS", str(len(rows)))
    monkeypatch.setenv("HLX_HOLDOUT_MANIFESTS", str(manifest))
    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "1")


def test_same_row_id_is_not_eligible():
    row = _row("cobalt lantern")
    reason = exclusion_reason(
        row,
        train_ids={row_id(row)},
        train_hashes=set(),
        other_ids=set(),
        other_hashes=set(),
    )
    assert reason == "train_row_id"


def test_same_normalized_text_different_row_id_is_not_eligible():
    train = _row("Blue Quartz Lantern!", split="train")
    hold = _row("blue quartz lantern", split="val", cls="INFERRED", lineage="none")
    assert row_id(train) != row_id(hold)
    assert normalized_text_sha256(train["text"]) == normalized_text_sha256(hold["text"])
    reason = exclusion_reason(
        hold,
        train_ids=set(),
        train_hashes={normalized_text_sha256(train["text"])},
        other_ids=set(),
        other_hashes=set(),
    )
    assert reason == "train_text_hash"


def test_different_text_is_eligible():
    row = _row("north cobble path", split="val")
    reason = exclusion_reason(
        row,
        train_ids=set(),
        train_hashes={normalized_text_sha256("other phrase")},
        other_ids=set(),
        other_hashes=set(),
    )
    assert reason == "eligible"


def test_draw_and_filter_share_the_canonical_normalizer():
    surface = "Hello, World! https://example.com/a"
    assert normalize_group_text(surface) == "hello world"
    digest = hashlib.sha256(normalize_group_text(surface).encode("utf-8")).hexdigest()
    assert digest == normalized_text_sha256(surface)
    assert normalized_text_sha256("Hello World") == digest


def test_text_collision_fails_controlled_preflight(monkeypatch, tmp_path, capsys):
    train = [_row(f"train row {i}") for i in range(3)]
    collided = _row("train row 1", split="val", task="unbind", lineage="none")
    manifest = _manifest(tmp_path / "holdout.json", [collided])
    _arm(monkeypatch, tmp_path, train, manifest)
    trunk = tmp_path / "trunk"
    trunk.mkdir()
    (trunk / "config.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("HYPERLEX_TRUNK_DIR", str(trunk))
    monkeypatch.setattr("hyperlexical.preflight.export_dataset", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("export")))
    assert preflight_main() == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "ADMISSION_FAIL"
    assert "CONTROLLED_RESERVE" in report["error"]


def test_row_id_collision_fails_controlled_preflight(monkeypatch, tmp_path, capsys):
    train = [_row("unique cobalt")]
    manifest = _manifest(tmp_path / "holdout.json", train)
    _arm(monkeypatch, tmp_path, train, manifest)
    trunk = tmp_path / "trunk"
    trunk.mkdir()
    (trunk / "config.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("HYPERLEX_TRUNK_DIR", str(trunk))
    monkeypatch.setattr(
        "hyperlexical.preflight.export_dataset",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("export")),
    )
    assert preflight_main() == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "ADMISSION_FAIL"
    assert "CONTROLLED_RESERVE" in report["error"]


def test_disjoint_holdout_is_admissible(monkeypatch, tmp_path, capsys):
    train = [_row(f"train row {i}") for i in range(4)]
    hold = _row("fresh holdout phrase", split="val")
    manifest = _manifest(tmp_path / "holdout.json", [hold])
    _arm(monkeypatch, tmp_path, train, manifest)
    trunk = tmp_path / "trunk"
    trunk.mkdir()
    (trunk / "config.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("HYPERLEX_TRUNK_DIR", str(trunk))
    monkeypatch.setattr(
        "hyperlexical.preflight.export_dataset",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("export")),
    )
    assert preflight_main() == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "ADMISSION_FAIL"
    assert report["status"] != "TRAINING_READY"
    assert "CONTROLLED_RESERVE" in report["error"]


def test_pinned_disjoint_holdout_keeps_all_9150_rows(monkeypatch, tmp_path):
    rows = [_row(f"pinned sentence {i}") for i in range(9150)]
    hold = _row("outside the pin", split="val", task="unbind", lineage="none")
    manifest = _manifest(tmp_path / "holdout.json", [hold])
    _arm(monkeypatch, tmp_path, rows, manifest)
    called = {"n": 0}

    def _export(*_args, **_kwargs):
        called["n"] += 1
        raise AssertionError("export_dataset")

    bundle = load_training_bundle(
        tmp_path,
        include_live=True,
        live_store=None,
        export_dataset=_export,
    )
    assert called["n"] == 0
    assert len(bundle["rows"]) == 9150
    spec = load_holdout_spec()
    report = assert_pinned_holdout_disjoint(bundle["rows"], spec)
    kept, removed = filter_holdout_rows(list(bundle["rows"]), spec)
    assert report["holdout_filter_training_rows_removed"] == 0
    assert removed == 0
    assert len(kept) == 9150


def test_colliding_holdout_never_reaches_the_trainer(monkeypatch, tmp_path):
    train = [_row("shared surface")]
    hold = _row("Shared Surface", split="val")
    manifest = _manifest(tmp_path / "holdout.json", [hold])
    _arm(monkeypatch, tmp_path, train, manifest)
    bundle = load_training_bundle(
        tmp_path,
        include_live=True,
        live_store=None,
        export_dataset=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("export")),
    )
    spec = load_holdout_spec()
    reached = {"trainer": False}
    with pytest.raises(SystemExit, match="ADMISSION FAIL"):
        assert_pinned_holdout_disjoint(bundle["rows"], spec)
        reached["trainer"] = True
    assert reached["trainer"] is False
    kept, removed = filter_holdout_rows(list(bundle["rows"]), spec)
    assert removed == 1
    assert len(kept) == 0


def test_abandoned_lifecycle_is_not_admissible(monkeypatch, tmp_path):
    manifest = _manifest(tmp_path / "holdout.json", [_row("historical phrase", split="val")])
    digest = _sha(manifest)
    before = manifest.read_bytes()
    (tmp_path / "holdout-lifecycle.json").write_text(
        json.dumps(
            {
                "schema": "hyperlex.holdout_lifecycle.v1",
                "status": "UNSCORED_ABANDONED",
                "reason": "EXPERIMENT_CLOSED_BEFORE_VALID_EXECUTION",
                "manifest_sha256": digest,
                "reusable": False,
                "scored": False,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "1")
    monkeypatch.setenv("HLX_EXPERIMENT_ID", "HLX-EXP-TEST")
    monkeypatch.setenv("HLX_HOLDOUT_MANIFESTS", str(manifest))
    with pytest.raises(SystemExit, match="UNSCORED_ABANDONED"):
        require_holdout_for_training()
    assert manifest.read_bytes() == before


def test_census_excludes_text_collisions_and_abandoned_ids():
    train = [_row("shared surface"), _row("train only")]
    abandoned = _row("abandoned phrase", split="val")
    fresh = _row("fresh phrase", split="val", task="unbind", lineage="none")
    source = [
        _row("test row", split="test"),
        train[0],
        _row("Shared Surface", split="val", cls="INFERRED"),
        abandoned,
        fresh,
    ]
    report = census(source, train, extra_rows=[abandoned])
    assert report["source_rows"] == 5
    assert report["excluded_by_split_test"] == 1
    assert report["excluded_by_training_row_id"] == 1
    assert report["excluded_by_training_normalized_text_hash"] == 1
    assert report["excluded_by_spent_or_abandoned"] == 1
    assert report["eligible_rows"] == 1
    assert report["unbind_eligible"] == 1
    assert report["waterfall_sums_to_source"] is True
