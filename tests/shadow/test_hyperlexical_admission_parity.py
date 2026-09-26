"""Preflight and the trainer share one admission result."""

from __future__ import annotations

import hashlib
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
        "HLX_THRESHOLD_AUTHORIZATION",
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
    assert "HLX_THRESHOLD_AUTHORIZATION" in material
    assert material["HLX_THRESHOLD_AUTHORIZATION"] is None
    first = effective_environment_hash()
    monkeypatch.setenv("HLX_THRESHOLD_AUTHORIZATION", "/tmp/not-a-file")
    assert effective_environment_hash() != first
    monkeypatch.delenv("HLX_THRESHOLD_AUTHORIZATION")
    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "0")
    assert effective_environment_hash() != first


def test_controlled_reserve_passes_preflight_and_admission_only(monkeypatch, tmp_path, capsys):
    armed = arm_controlled(monkeypatch, tmp_path, [classify_row(f"train {i}") for i in range(8)])
    code, pre = _pair(monkeypatch, capsys)
    assert code == 0
    assert pre["admission_result"] == "ADMISSION_PASS"
    assert pre["status"] == "PREREGISTERED"
    assert pre["ready_to_train"] is False
    assert pre["scientific_contract_sealed"] is True
    assert pre["decision_rule_sealed"] is False
    assert pre["decision_threshold_state"] == "BLOCKED_PENDING_OPERATOR_AUTHORIZATION"
    assert pre["training_launch_authorized"] is False
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
    assert launch["status"] == "PREREGISTERED"
    assert launch["ready_to_train"] is False
    assert launch["environment_hash"] == pre["environment_hash"]
    assert launch["admission_gate_sequence"] == pre["admission_gate_sequence"]
    assert launch["epochs"] == 0
    assert launch["optimizer_loaded"] is False
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


def _write_thresholds(tmp_path: Path, **overrides) -> Path:
    payload = {
        "schema": "hyperlex.threshold_authorization.v1",
        "experiment_id": "HLX-EXP-TEST",
        "sealed": True,
        "decision_thresholds": {"unbind_clean_exact": 0.5},
    }
    payload.update(overrides)
    path = tmp_path / "threshold-authorization.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_sealed_decision_rule_reaches_training_ready(monkeypatch, tmp_path, capsys):
    arm_controlled(monkeypatch, tmp_path, [classify_row(f"train {i}") for i in range(4)])
    path = _write_thresholds(tmp_path)
    monkeypatch.setenv("HLX_THRESHOLD_AUTHORIZATION", str(path))
    code, pre = _pair(monkeypatch, capsys)
    assert code == 0
    assert pre["admission_result"] == "ADMISSION_PASS"
    assert pre["status"] == "TRAINING_READY"
    assert pre["ready_to_train"] is True
    assert pre["decision_rule_sealed"] is True
    assert pre["decision_threshold_state"] == "SEALED"
    assert pre["training_launch_authorized"] is False
    assert pre["optimizer_loaded"] is False
    launch_code, launch = _launch(capsys)
    assert launch_code == 0
    assert launch["status"] == pre["status"]
    assert launch["environment_hash"] == pre["environment_hash"]
    assert launch["optimizer_loaded"] is False


def test_threshold_authorization_for_another_experiment_rejects_both(monkeypatch, tmp_path, capsys):
    arm_controlled(monkeypatch, tmp_path, [classify_row("train row")])
    path = _write_thresholds(tmp_path, experiment_id="HLX-EXP-OTHER")
    monkeypatch.setenv("HLX_THRESHOLD_AUTHORIZATION", str(path))
    pre = _assert_same_failure(monkeypatch, capsys)
    assert "experiment_id does not match" in pre["error"]
    assert pre["failed_gate"] == "ready"
    assert pre["status"] == "ADMISSION_FAIL"


def test_unsealed_threshold_authorization_rejects_both(monkeypatch, tmp_path, capsys):
    arm_controlled(monkeypatch, tmp_path, [classify_row("train row")])
    path = _write_thresholds(tmp_path, sealed=False)
    monkeypatch.setenv("HLX_THRESHOLD_AUTHORIZATION", str(path))
    pre = _assert_same_failure(monkeypatch, capsys)
    assert "not sealed" in pre["error"]
    assert pre["failed_gate"] == "ready"


def _rebind_ledger(monkeypatch, tmp_path: Path, armed: dict, ledger) -> None:
    directory = tmp_path / "ledger-rebound"
    ledger.save(directory)
    binding_path = Path(armed["reserve"]["binding"])
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256((directory / "events.jsonl").read_bytes()).hexdigest()
    binding["ledger_events_sha256"] = digest
    rebound = tmp_path / "reserve-binding-rebound.json"
    rebound.write_text(json.dumps(binding), encoding="utf-8")
    monkeypatch.setenv("HLX_EVAL_RESERVE_LEDGER", str(directory))
    monkeypatch.setenv("HLX_RESERVE_BINDING", str(rebound))


def test_historical_spent_identity_is_not_the_controlled_reserve(monkeypatch, tmp_path, capsys):
    from hyperlexical.identity_ledger import IdentityLedger

    armed = arm_controlled(monkeypatch, tmp_path, [classify_row("train row")])
    ledger = IdentityLedger.load(armed["reserve"]["ledger"])
    ledger.mark_historical(
        "ab" * 32,
        "evaluation_spent",
        source_artifact="historical-fixture",
        provenance="fixture",
    )
    _rebind_ledger(monkeypatch, tmp_path, armed, ledger)
    code, pre = _pair(monkeypatch, capsys)
    assert code == 0
    assert pre["admission_result"] == "ADMISSION_PASS"
    assert pre["status"] == "PREREGISTERED"
    assert pre["reserve_lifecycle"] == "EVAL_RESERVE"


def test_reserve_identity_that_left_eval_reserve_rejects_both(monkeypatch, tmp_path, capsys):
    from hyperlexical.identity_ledger import IdentityLedger, derived_state

    armed = arm_controlled(monkeypatch, tmp_path, [classify_row("train row")])
    ledger = IdentityLedger.load(armed["reserve"]["ledger"])
    reserved = [
        digest
        for digest, record in ledger.identities.items()
        if derived_state(record) == "EVAL_RESERVE"
    ]
    ledger.transition(
        reserved[0],
        "EVAL_BOUND",
        source_artifact="fixture",
        provenance="fixture",
    )
    _rebind_ledger(monkeypatch, tmp_path, armed, ledger)
    pre = _assert_same_failure(monkeypatch, capsys)
    assert "EVAL_BOUND" in pre["error"]
    assert pre["failed_gate"] == "holdout_reserve"


def test_allow_no_holdout_rejects_both(monkeypatch, tmp_path, capsys):
    arm_controlled(monkeypatch, tmp_path, [classify_row("train row")])
    monkeypatch.setenv("HLX_ALLOW_NO_HOLDOUT", "1")
    pre = _assert_same_failure(monkeypatch, capsys)
    assert "HLX_ALLOW_NO_HOLDOUT" in pre["error"]
    assert pre["failed_gate"] == "experiment_binding"
