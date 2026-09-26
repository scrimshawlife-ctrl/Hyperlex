"""Preflight and the trainer share one admission result."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from admission_fixtures import arm_controlled, classify_row  # noqa: E402
from hyperlexical.admission import (  # noqa: E402
    effective_environment_hash,
    effective_environment_material,
)
from hyperlexical.preflight import main as preflight_main  # noqa: E402
from hyperlexical import train as train_mod  # noqa: E402


@pytest.fixture(autouse=True)
def _clear(monkeypatch):
    for key in (
        "HLX_TRAIN_EXPORT_PATH",
        "HLX_TRAIN_EXPORT_SHA256",
        "HLX_TRAIN_EXPORT_ROWS",
        "HLX_EXPERIMENT_ID",
        "HLX_HOLDOUT_MANIFESTS",
        "HLX_ALLOW_NO_HOLDOUT",
        "HLX_ADMISSION_ONLY",
        "HLX_EVAL_RESERVE_LEDGER",
        "HLX_RESERVE_BINDING",
        "HLX_BASELINE_ENV",
        "HLX_CANDIDATE_ENV",
        "HLX_SELECT_METRIC",
        "HLX_BEST_SHA256",
        "HLX_BEST_WEIGHTS",
        "HLX_TRUNK_SHA256",
        "HYPERLEX_ALLOW_TRAIN",
        "HYPERLEX_INCLUDE_LIVE",
        "HYPERLEX_EXPORT_DIR",
        "HYPERLEX_TRAIN_OUT",
        "HYPERLEX_TRUNK_DIR",
        "HYPERLEX_FILLER_FILTER",
        "HYPERLEX_RELEASE_SET",
    ):
        monkeypatch.delenv(key, raising=False)


def _refuse_export(*_args, **_kwargs):
    raise AssertionError("export_dataset must not run")


def _refuse_train():
    raise AssertionError("training execution was reached")


def _pair(monkeypatch, capsys):
    monkeypatch.setenv("HLX_ADMISSION_ONLY", "1")
    monkeypatch.setattr("hyperlexical.preflight.export_dataset", _refuse_export)
    monkeypatch.setattr("hyperlexical.loop.export_dataset", _refuse_export)
    monkeypatch.setattr("hyperlexical.loop._enter_training_execution", _refuse_train)
    pre_code = preflight_main()
    pre = json.loads(capsys.readouterr().out)
    return pre_code, pre


def _launch(capsys):
    try:
        code = train_mod.main(["--offline", "--run", "--include-live"])
    except SystemExit as exc:
        err = capsys.readouterr()
        return exc, err
    out = json.loads(capsys.readouterr().out)
    return code, out


def test_environment_hash_includes_launch_overlay_and_skips_admission_only(monkeypatch):
    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "1")
    monkeypatch.setenv("HLX_ADMISSION_ONLY", "1")
    material = effective_environment_material()
    assert material["HYPERLEX_ALLOW_TRAIN"] == "1"
    assert "HLX_ADMISSION_ONLY" not in material
    first = effective_environment_hash()
    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "0")
    assert effective_environment_hash() != first


def test_controlled_reserve_passes_preflight_and_admission_only(monkeypatch, tmp_path, capsys):
    armed = arm_controlled(monkeypatch, tmp_path, [classify_row(f"train {i}") for i in range(8)])
    code, pre = _pair(monkeypatch, capsys)
    assert code == 0
    assert pre["admission_result"] == "ADMISSION_PASS"
    assert pre["status"] == "TRAINING_READY"
    assert pre["controlled_holdout_contract"] == "CONTROLLED_RESERVE"
    assert pre["training_input_mode"] == "PINNED_EXPORT"
    assert pre["training_export_sha256_actual"] == armed["digest"]
    assert pre["training_export_rows"] == 8
    assert pre["live_export_generation_enabled"] is False
    assert pre["reserve_train_row_id_overlap"] == 0
    assert pre["reserve_train_text_hash_overlap"] == 0
    assert pre["training_rows_removed"] == 0
    assert pre["epochs"] == 0
    assert pre["gradient_steps"] == 0
    assert pre["optimizer_loaded"] is False
    assert pre["training_started"] is False
    assert pre["hlx_allow_no_holdout"] is False
    launch_code, launch = _launch(capsys)
    assert launch_code == 0
    assert launch["admission_result"] == pre["admission_result"]
    assert launch["environment_hash"] == pre["environment_hash"]
    assert launch["admission_gate_sequence"] == pre["admission_gate_sequence"]
    assert launch["epochs"] == 0
    assert not armed["out"].exists()


def _assert_same_failure(monkeypatch, capsys):
    code, pre = _pair(monkeypatch, capsys)
    assert code == 2
    assert pre["admission_result"] == "ADMISSION_FAIL"
    assert pre["status"] == "ADMISSION_FAIL"
    exc, _err = _launch(capsys)
    assert isinstance(exc, SystemExit)
    assert str(exc) == pre["error"]
    assert exc.receipt["environment_hash"] == pre["environment_hash"]
    assert exc.receipt["admission_gate_sequence"] == pre["admission_gate_sequence"]
    assert exc.receipt["failed_gate"] == pre["failed_gate"]
    return pre


def test_missing_pin_rejects_both(monkeypatch, tmp_path, capsys):
    arm_controlled(monkeypatch, tmp_path, [classify_row("train row")])
    monkeypatch.delenv("HLX_TRAIN_EXPORT_PATH")
    monkeypatch.delenv("HLX_TRAIN_EXPORT_SHA256")
    monkeypatch.delenv("HLX_TRAIN_EXPORT_ROWS")
    pre = _assert_same_failure(monkeypatch, capsys)
    assert "no pinned export" in pre["error"]
    assert pre["failed_gate"] == "pinned_training_input"


def test_missing_reserve_rejects_both(monkeypatch, tmp_path, capsys):
    arm_controlled(monkeypatch, tmp_path, [classify_row("train row")])
    monkeypatch.delenv("HLX_EVAL_RESERVE_LEDGER")
    monkeypatch.delenv("HLX_RESERVE_BINDING")
    pre = _assert_same_failure(monkeypatch, capsys)
    assert "no sealed evaluation reserve" in pre["error"]
    assert pre["failed_gate"] == "holdout_reserve"


def test_pinned_digest_mismatch_rejects_both(monkeypatch, tmp_path, capsys):
    arm_controlled(monkeypatch, tmp_path, [classify_row("train row")])
    monkeypatch.setenv("HLX_TRAIN_EXPORT_SHA256", "b" * 64)
    pre = _assert_same_failure(monkeypatch, capsys)
    assert "digest mismatch" in pre["error"]
    assert pre["failed_gate"] == "pinned_training_input"


def test_reserve_overlap_rejects_both(monkeypatch, tmp_path, capsys):
    arm_controlled(
        monkeypatch,
        tmp_path,
        [classify_row("reserve classify surface")],
    )
    pre = _assert_same_failure(monkeypatch, capsys)
    assert "overlaps the sealed reserve" in pre["error"]
    assert pre["failed_gate"] == "train_reserve_disjointness"
    assert pre["training_rows_removed"] == 0


def test_second_scientific_variable_rejects_both(monkeypatch, tmp_path, capsys):
    arm_controlled(
        monkeypatch,
        tmp_path,
        [classify_row("train row")],
        candidate_extra={"HYPERLEX_TASK_ROUTING": "route_rows"},
    )
    pre = _assert_same_failure(monkeypatch, capsys)
    assert "scientific variable count" in pre["error"]
    assert pre["failed_gate"] == "single_variable"


def test_best_mismatch_rejects_both(monkeypatch, tmp_path, capsys):
    arm_controlled(
        monkeypatch,
        tmp_path,
        [classify_row("train row")],
        best_sha="c" * 64,
    )
    pre = _assert_same_failure(monkeypatch, capsys)
    assert "BEST weights sha256 mismatch" in pre["error"]
    assert pre["failed_gate"] == "best_trunk"


def test_trunk_mismatch_rejects_both(monkeypatch, tmp_path, capsys):
    arm_controlled(
        monkeypatch,
        tmp_path,
        [classify_row("train row")],
        trunk_sha="d" * 64,
    )
    pre = _assert_same_failure(monkeypatch, capsys)
    assert "trunk weights sha256 mismatch" in pre["error"]
    assert pre["failed_gate"] == "best_trunk"


def test_output_directory_collision_rejects_both(monkeypatch, tmp_path, capsys):
    arm_controlled(
        monkeypatch,
        tmp_path,
        [classify_row("train row")],
        create_output=True,
    )
    pre = _assert_same_failure(monkeypatch, capsys)
    assert "output directory collision" in pre["error"]
    assert pre["failed_gate"] == "output_directory"


def test_allow_no_holdout_rejects_both(monkeypatch, tmp_path, capsys):
    arm_controlled(monkeypatch, tmp_path, [classify_row("train row")])
    monkeypatch.setenv("HLX_ALLOW_NO_HOLDOUT", "1")
    pre = _assert_same_failure(monkeypatch, capsys)
    assert "HLX_ALLOW_NO_HOLDOUT" in pre["error"]
    assert pre["failed_gate"] == "experiment_binding"
