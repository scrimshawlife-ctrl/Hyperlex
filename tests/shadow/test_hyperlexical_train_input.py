"""Pinned export is the training input. Existence of a file is not use."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.loop import run_loop  # noqa: E402
from hyperlexical.preflight import main as preflight_main  # noqa: E402
from hyperlexical.training_routing import route_rows as real_route_rows  # noqa: E402
from hyperlexical.train_input import train_input_receipt as real_train_input_receipt  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_pin_env(monkeypatch):
    for key in (
        "HLX_TRAIN_EXPORT_PATH",
        "HLX_TRAIN_EXPORT_SHA256",
        "HLX_TRAIN_EXPORT_ROWS",
        "HLX_EXPERIMENT_ID",
        "HLX_HOLDOUT_MANIFESTS",
        "HLX_ALLOW_NO_HOLDOUT",
        "HYPERLEX_ALLOW_TRAIN",
        "HYPERLEX_INCLUDE_LIVE",
        "HYPERLEX_EXPORT_DIR",
        "HYPERLEX_RELEASE_SET",
        "HYPERLEX_TASK_ROUTING",
        "HYPERLEX_TRUNK_DIR",
        "HYPERLEX_LIVE_STORE",
    ):
        monkeypatch.delenv(key, raising=False)


def _classify(text: str) -> dict:
    return {
        "text": text,
        "task": "classify",
        "split": "train",
        "class": "OBSERVED",
        "lineage": "none",
        "role_scheme": "positional",
    }


def _write_export(path: Path, rows: list[dict]) -> str:
    payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.write_text(payload, encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _refuse_export(*_args, **_kwargs):
    raise AssertionError("export_dataset must not run")


def _pin(monkeypatch, tmp_path: Path, rows: list[dict], *, rows_env: str | None = None) -> tuple[Path, str]:
    path = tmp_path / "pinned.jsonl"
    digest = _write_export(path, rows)
    monkeypatch.setenv("HLX_EXPERIMENT_ID", "HLX-EXP-TEST")
    monkeypatch.setenv("HLX_TRAIN_EXPORT_PATH", str(path))
    monkeypatch.setenv("HLX_TRAIN_EXPORT_SHA256", digest)
    monkeypatch.setenv("HYPERLEX_EXPORT_DIR", str(tmp_path / "export-out"))
    if rows_env is not None:
        monkeypatch.setenv("HLX_TRAIN_EXPORT_ROWS", rows_env)
    return path, digest


def test_pinned_export_is_consumed_and_recorded(monkeypatch, tmp_path):
    marker = "pinned quartz marker"
    path, digest = _pin(monkeypatch, tmp_path, [_classify(marker)], rows_env="1")
    seen: dict = {}

    def _route(rows):
        seen["texts"] = [row.get("text") for row in rows]
        return real_route_rows(rows)

    def _receipt(bundle):
        fields = real_train_input_receipt(bundle)
        seen["receipt"] = fields
        seen["loaded_texts"] = [row.get("text") for row in bundle["rows"]]
        return fields

    monkeypatch.setattr("hyperlexical.loop.export_dataset", _refuse_export)
    monkeypatch.setattr("hyperlexical.loop.route_rows", _route)
    monkeypatch.setattr("hyperlexical.loop.train_input_receipt", _receipt)
    with pytest.raises(RuntimeError, match="not enough classify train rows"):
        run_loop(
            tmp_path,
            tmp_path / "out",
            include_live=True,
            live_store=tmp_path / "live-would-be-used.jsonl",
        )
    assert seen["texts"] == [marker]
    assert seen["loaded_texts"] == [marker]
    receipt = seen["receipt"]
    assert receipt["training_input_mode"] == "PINNED_EXPORT"
    assert receipt["training_export_path"] == str(path.resolve())
    assert receipt["training_export_sha256_expected"] == digest
    assert receipt["training_export_sha256_actual"] == digest
    assert receipt["data_sha256"] == digest
    assert receipt["training_export_rows"] == 1
    assert receipt["live_export_generation_enabled"] is False


def test_pinned_export_missing_is_rejected(monkeypatch, tmp_path):
    missing = tmp_path / "absent.jsonl"
    monkeypatch.setenv("HLX_EXPERIMENT_ID", "HLX-EXP-TEST")
    monkeypatch.setenv("HLX_TRAIN_EXPORT_PATH", str(missing))
    monkeypatch.setenv("HLX_TRAIN_EXPORT_SHA256", "a" * 64)
    monkeypatch.setattr("hyperlexical.loop.export_dataset", _refuse_export)
    with pytest.raises(SystemExit, match="pinned export missing"):
        run_loop(tmp_path, tmp_path / "out", include_live=True)


def test_pinned_export_digest_mismatch_is_rejected(monkeypatch, tmp_path):
    path = tmp_path / "pinned.jsonl"
    _write_export(path, [_classify("pinned quartz marker")])
    monkeypatch.setenv("HLX_EXPERIMENT_ID", "HLX-EXP-TEST")
    monkeypatch.setenv("HLX_TRAIN_EXPORT_PATH", str(path))
    monkeypatch.setenv("HLX_TRAIN_EXPORT_SHA256", "b" * 64)
    monkeypatch.setattr("hyperlexical.loop.export_dataset", _refuse_export)
    with pytest.raises(SystemExit, match="digest mismatch"):
        run_loop(tmp_path, tmp_path / "out", include_live=True)


def test_experiment_without_pinned_export_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setenv("HLX_EXPERIMENT_ID", "HLX-EXP-TEST")
    monkeypatch.setattr("hyperlexical.loop.export_dataset", _refuse_export)
    with pytest.raises(SystemExit, match="no pinned export"):
        run_loop(tmp_path, tmp_path / "out", include_live=True, live_store=tmp_path / "store.jsonl")


def test_pinned_row_count_mismatch_is_rejected(monkeypatch, tmp_path):
    _pin(monkeypatch, tmp_path, [_classify("pinned quartz marker")], rows_env="9150")
    monkeypatch.setattr("hyperlexical.loop.export_dataset", _refuse_export)
    with pytest.raises(SystemExit, match="row count mismatch"):
        run_loop(tmp_path, tmp_path / "out")


def test_live_build_outside_controlled_experiment_still_exports(monkeypatch, tmp_path):
    captured: dict = {}

    def fake_export(root, include_live=False, live_store=None):
        captured["include_live"] = include_live
        captured["live_store"] = live_store
        raise RuntimeError("stop-before-torch")

    monkeypatch.setattr("hyperlexical.loop.export_dataset", fake_export)
    with pytest.raises(RuntimeError, match="stop-before-torch"):
        run_loop(tmp_path, tmp_path / "out", include_live=True, live_store=tmp_path / "store.jsonl")
    assert captured["include_live"] is True
    assert captured["live_store"] == tmp_path / "store.jsonl"



def _seal_holdout(tmp_path: Path, experiment_id: str = "HLX-EXP-TEST") -> Path:
    path = tmp_path / "holdout.json"
    path.write_text(
        json.dumps(
            {
                "schema": "hyperlex.holdout_manifest.v2",
                "status": "UNSCORED_SEALED",
                "experiment_id": experiment_id,
                "row_ids": ["abc123"],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_preflight_pinned_proves_loader_without_export(monkeypatch, tmp_path, capsys):
    """A legacy manifest does not admit a controlled experiment."""
    _pin(monkeypatch, tmp_path, [_classify("pinned quartz marker")], rows_env="1")
    trunk = tmp_path / "trunk"
    trunk.mkdir()
    (trunk / "config.json").write_text("{}\n", encoding="utf-8")
    manifest = _seal_holdout(tmp_path)
    monkeypatch.setenv("HLX_HOLDOUT_MANIFESTS", str(manifest))
    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "1")
    monkeypatch.setenv("HYPERLEX_TRUNK_DIR", str(trunk))
    monkeypatch.setattr("hyperlexical.preflight.export_dataset", _refuse_export)
    assert preflight_main() == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "ADMISSION_FAIL"
    assert report["ready_to_train"] is False
    assert report["holdout_admitted"] is False
    assert "CONTROLLED_RESERVE" in report["error"]


def test_preflight_controlled_without_holdout_is_rejected(monkeypatch, tmp_path, capsys):
    _pin(monkeypatch, tmp_path, [_classify("pinned quartz marker")], rows_env="1")
    trunk = tmp_path / "trunk"
    trunk.mkdir()
    (trunk / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "1")
    monkeypatch.setenv("HYPERLEX_TRUNK_DIR", str(trunk))
    monkeypatch.setattr("hyperlexical.preflight.export_dataset", _refuse_export)
    assert preflight_main() == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "ADMISSION_FAIL"
    assert report["ready_to_train"] is False
    assert report["holdout_admitted"] is False
    assert "no sealed evaluation reserve" in report["error"]


def test_pinned_experiment_without_holdout_is_rejected(monkeypatch, tmp_path):
    _pin(monkeypatch, tmp_path, [_classify("pinned quartz marker")], rows_env="1")
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "1")
    monkeypatch.setenv("HYPERLEX_TRUNK_DIR", str(tmp_path))
    monkeypatch.setattr("hyperlexical.loop.export_dataset", _refuse_export)
    with pytest.raises(SystemExit, match="no sealed evaluation reserve"):
        run_loop(tmp_path, tmp_path / "out", include_live=True)


def test_preflight_experiment_without_pin_is_not_training_ready(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("HLX_EXPERIMENT_ID", "HLX-EXP-TEST")
    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "1")
    trunk = tmp_path / "trunk"
    trunk.mkdir()
    (trunk / "config.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("HYPERLEX_TRUNK_DIR", str(trunk))
    monkeypatch.setattr("hyperlexical.preflight.export_dataset", _refuse_export)
    assert preflight_main() == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "ADMISSION_FAIL"
    assert report["ready_to_train"] is False
    assert report["status"] != "TRAINING_READY"
    assert "no sealed evaluation reserve" in report["error"]


def test_preflight_live_build_still_calls_export(monkeypatch, tmp_path, capsys):
    captured: dict = {}

    def fake_export(root, include_live=False, live_store=None):
        captured["include_live"] = include_live
        captured["called"] = True
        return {
            "rows": [],
            "sha256": "abc",
            "counts": {"n": 0, "live_included": 0},
            "payload": "",
        }

    monkeypatch.setattr("hyperlexical.preflight.export_dataset", fake_export)
    assert preflight_main() == 2
    report = json.loads(capsys.readouterr().out)
    assert captured["called"] is True
    assert captured["include_live"] is False
    assert report["training_input_mode"] == "LIVE_BUILD"
    assert report["live_export_generation_enabled"] is True
    assert report["data_sha256"] == "abc"
    assert report["status"] != "TRAINING_READY"
