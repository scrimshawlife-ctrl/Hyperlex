"""The SELECT-006 candidate schedule is the default. A preregistration overrides it."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from hyperlexical.classify_metrics import SELECT_METRIC_CLASSIFY, SELECT_METRIC_UNBIND
from hyperlexical.select_006_efficiency_preservation import baseline_env, candidate_env
from hyperlexical.training_schedule import (
    SOURCE_DEFAULT,
    SOURCE_HISTORICAL,
    SOURCE_PREREGISTERED,
    ScheduleError,
    environment_for_schedule,
    install_default_schedule,
    resolve_training_schedule,
    select_006_candidate_schedule,
)
import hyperlexical.loop as loop


def test_comparable_run_defaults_to_the_select_006_candidate_schedule():
    schedule = resolve_training_schedule(select_metric=SELECT_METRIC_CLASSIFY, environ={})
    sealed = candidate_env()
    assert schedule.source == SOURCE_DEFAULT
    assert schedule.max_epochs == int(sealed["HYPERLEX_TRAIN_EPOCHS"])
    assert schedule.patience == int(sealed["HYPERLEX_EARLY_STOP_PATIENCE"])
    assert schedule.minimum_epochs == int(sealed["HYPERLEX_EARLY_STOP_MIN_EPOCHS"])
    assert schedule.early_stopping is True
    assert schedule.improvement == "strict"
    assert schedule.ties == "keep_earlier"
    assert schedule.restore_best is True
    assert schedule == select_006_candidate_schedule()


def test_unbind_runs_keep_the_historical_unset_schedule():
    schedule = resolve_training_schedule(select_metric=SELECT_METRIC_UNBIND, environ={})
    assert schedule.source == SOURCE_HISTORICAL
    assert schedule.max_epochs == 2
    assert schedule.early_stopping is False
    assert schedule.patience is None


def test_explicit_environment_overrides_the_default():
    control = baseline_env()
    schedule = resolve_training_schedule(
        select_metric=SELECT_METRIC_CLASSIFY,
        environ=control,
    )
    assert schedule.source == SOURCE_PREREGISTERED
    assert schedule.max_epochs == 40
    assert schedule.early_stopping is False
    assert schedule.patience is None
    assert control["HYPERLEX_TRAIN_EPOCHS"] == "40"
    assert control["HYPERLEX_EARLY_STOP"] == "0"


def test_preregistered_schedule_overrides_the_default_and_must_match_the_environment():
    declared = {
        "training_schedule": {
            "early_stopping": "disabled",
            "max_epochs": 40,
            "restore_best": True,
        }
    }
    schedule = resolve_training_schedule(
        select_metric=SELECT_METRIC_CLASSIFY,
        environ={},
        preregistered=declared,
    )
    assert schedule.source == SOURCE_PREREGISTERED
    assert schedule.max_epochs == 40
    assert schedule.early_stopping is False
    overlay = environment_for_schedule(schedule)
    assert overlay == {"HYPERLEX_EARLY_STOP": "0", "HYPERLEX_TRAIN_EPOCHS": "40"}
    agreed = resolve_training_schedule(
        select_metric=SELECT_METRIC_CLASSIFY,
        environ=overlay,
        preregistered=declared,
    )
    assert agreed.max_epochs == 40
    with pytest.raises(ScheduleError, match="does not match"):
        resolve_training_schedule(
            select_metric=SELECT_METRIC_CLASSIFY,
            environ={"HYPERLEX_TRAIN_EPOCHS": "6", "HYPERLEX_EARLY_STOP": "0"},
            preregistered=declared,
        )


def test_two_arm_preregistration_requires_an_explicit_arm():
    both = {
        "candidate_schedule": {"max_epochs": 12, "early_stopping_patience": 4, "minimum_epochs": 4},
        "control_schedule": {"early_stopping": "disabled", "max_epochs": 40, "restore_best": True},
    }
    with pytest.raises(ScheduleError, match="schedule_arm"):
        resolve_training_schedule(
            select_metric=SELECT_METRIC_CLASSIFY,
            environ={},
            preregistered=both,
        )
    control = resolve_training_schedule(
        select_metric=SELECT_METRIC_CLASSIFY,
        environ={},
        preregistered={**both, "schedule_arm": "control"},
    )
    assert control.max_epochs == 40 and control.early_stopping is False


def test_non_strict_override_is_rejected():
    with pytest.raises(ScheduleError, match="strict"):
        resolve_training_schedule(
            select_metric=SELECT_METRIC_CLASSIFY,
            environ={},
            preregistered={"improvement": "loose", "max_epochs": 6, "early_stopping": "disabled"},
        )


def test_install_default_does_not_replace_an_explicit_schedule():
    env = {"HYPERLEX_TRAIN_EPOCHS": "40", "HYPERLEX_EARLY_STOP": "0"}
    install_default_schedule(env)
    assert env["HYPERLEX_TRAIN_EPOCHS"] == "40"
    assert env["HYPERLEX_EARLY_STOP"] == "0"
    assert "HYPERLEX_EARLY_STOP_PATIENCE" not in env


def test_run_loop_resolves_the_schedule_before_admission_and_the_optimizer():
    tree = ast.parse(Path(loop.__file__).read_text(encoding="utf-8"))
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_loop")
    lines = {
        "resolve_training_schedule": None,
        "admit_training_run": None,
        "resolve_early_stop_config": None,
        "AdamW": None,
    }
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        if name in lines and lines[name] is None:
            lines[name] = node.lineno
    assert lines["resolve_training_schedule"] < lines["admit_training_run"]
    assert lines["resolve_early_stop_config"] < lines["AdamW"]
