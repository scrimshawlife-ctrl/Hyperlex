"""classify_sampling is one admission variable. Schedules stay shared."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from admission_fixtures import arm_controlled, classify_row  # noqa: E402
from hyperlexical.admission import AdmissionError, admit_training_run  # noqa: E402

RULE = "inferred_none_circular_sha256_v1:219"
SCHEDULE = {
    "HLX_SCIENTIFIC_VARIABLE": "classify_sampling",
    "HLX_SELECT_METRIC": "classify_macro_f1_nonnone",
    "HYPERLEX_EARLY_STOP": "1",
    "HYPERLEX_EARLY_STOP_MIN_EPOCHS": "4",
    "HYPERLEX_EARLY_STOP_PATIENCE": "4",
    "HYPERLEX_FILLER_FILTER": "off",
    "HYPERLEX_TRAIN_EPOCHS": "12",
}


def _admit():
    return admit_training_run(
        trunk=Path(__import__("os").environ["HYPERLEX_TRUNK_DIR"]),
        out_dir=Path(__import__("os").environ["HYPERLEX_TRAIN_OUT"]),
    )


def _bind(monkeypatch, tmp_path, *, candidate_extra=None, process_sampling=RULE, arm="candidate"):
    armed = arm_controlled(monkeypatch, tmp_path, [classify_row("train row")])
    baseline = {**SCHEDULE, "HYPERLEX_CLASSIFY_SAMPLING": "uncapped"}
    candidate = {
        **SCHEDULE,
        "HYPERLEX_CLASSIFY_SAMPLING": RULE,
        "HLX_EXPERIMENT_ID": "HLX-EXP-TEST",
        "HYPERLEX_TRAIN_OUT": str(armed["out"]),
    }
    if candidate_extra:
        candidate.update(candidate_extra)
    (tmp_path / "baseline-env.json").write_text(json.dumps(baseline, sort_keys=True), encoding="utf-8")
    (tmp_path / "candidate-env.json").write_text(json.dumps(candidate, sort_keys=True), encoding="utf-8")
    monkeypatch.setenv("HLX_SCIENTIFIC_VARIABLE", "classify_sampling")
    monkeypatch.setenv("HLX_SCHEDULE_ARM", arm)
    for key, value in candidate.items():
        if key in {"HLX_EXPERIMENT_ID", "HYPERLEX_TRAIN_OUT", "HLX_SCIENTIFIC_VARIABLE"}:
            continue
        monkeypatch.setenv(key, str(value))
    monkeypatch.setenv("HYPERLEX_CLASSIFY_SAMPLING", process_sampling)
    for key, value in SCHEDULE.items():
        if key != "HLX_SCIENTIFIC_VARIABLE":
            monkeypatch.setenv(key, value)
    return armed


def test_sampling_cap_is_the_only_variable(monkeypatch, tmp_path):
    _bind(monkeypatch, tmp_path)
    result = _admit()
    assert result.admission_result == "ADMISSION_PASS"


def test_control_arm_uses_the_uncapped_policy(monkeypatch, tmp_path):
    _bind(monkeypatch, tmp_path, process_sampling="uncapped", arm="control")
    result = _admit()
    assert result.admission_result == "ADMISSION_PASS"


def test_second_difference_is_refused(monkeypatch, tmp_path):
    _bind(monkeypatch, tmp_path, candidate_extra={"HYPERLEX_TRAIN_LR": "1e-4"})
    monkeypatch.setenv("HYPERLEX_TRAIN_LR", "1e-4")
    with pytest.raises(AdmissionError, match="scientific variable count is 2"):
        _admit()


def test_schedule_drift_is_not_part_of_sampling(monkeypatch, tmp_path):
    _bind(monkeypatch, tmp_path, candidate_extra={"HYPERLEX_TRAIN_EPOCHS": "40"})
    monkeypatch.setenv("HYPERLEX_TRAIN_EPOCHS", "40")
    with pytest.raises(AdmissionError, match="undeclared schedule difference"):
        _admit()
