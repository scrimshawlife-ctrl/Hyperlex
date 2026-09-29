"""Default training schedule for comparable Hyperlex runs.

Comparable runs select ``classify_macro_f1_nonnone``. When they do not
preregister a schedule, they use the SELECT-006 candidate schedule:
12 epochs, patience 4, minimum 4 scored epochs, strict improvement,
ties keep the earlier checkpoint, and the best checkpoint is restored.

A preregistered schedule replaces that default. Pass it as a mapping or
set its ``HYPERLEX_TRAIN_EPOCHS`` / ``HYPERLEX_EARLY_STOP`` variables.
Those explicit values are not rewritten.

Runs that do not select the classify metric keep the historical unset
schedule: 2 epochs and early stopping off.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping

from .classify_metrics import SELECT_METRIC_CLASSIFY

SOURCE_DEFAULT = "select-006-candidate"
SOURCE_PREREGISTERED = "preregistered"
SOURCE_HISTORICAL = "historical"

TRAIN_EPOCHS_ENV = "HYPERLEX_TRAIN_EPOCHS"
EARLY_STOP_ENV = "HYPERLEX_EARLY_STOP"
EARLY_STOP_PATIENCE_ENV = "HYPERLEX_EARLY_STOP_PATIENCE"
EARLY_STOP_MIN_EPOCHS_ENV = "HYPERLEX_EARLY_STOP_MIN_EPOCHS"

SCHEDULE_ENV_KEYS = (
    TRAIN_EPOCHS_ENV,
    EARLY_STOP_ENV,
    EARLY_STOP_PATIENCE_ENV,
    EARLY_STOP_MIN_EPOCHS_ENV,
)

_OFF = frozenset({"0", "false", "no", "off", "disabled"})
_ON = frozenset({"1", "true", "yes", "on", "enabled"})

HISTORICAL_MAX_EPOCHS = 2


class ScheduleError(ValueError):
    """A schedule override is incomplete or disagrees with the process."""


@dataclass(frozen=True)
class TrainingSchedule:
    max_epochs: int
    early_stopping: bool
    patience: int | None
    minimum_epochs: int | None
    improvement: str
    ties: str
    restore_best: bool
    source: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "early_stopping": self.early_stopping,
            "improvement": self.improvement,
            "max_epochs": self.max_epochs,
            "minimum_epochs": self.minimum_epochs,
            "patience": self.patience,
            "restore_best": self.restore_best,
            "source": self.source,
            "ties": self.ties,
        }


def select_006_candidate_schedule() -> TrainingSchedule:
    """The sealed SELECT-006 candidate schedule, as the comparable-run default."""
    return TrainingSchedule(
        max_epochs=12,
        early_stopping=True,
        patience=4,
        minimum_epochs=4,
        improvement="strict",
        ties="keep_earlier",
        restore_best=True,
        source=SOURCE_DEFAULT,
    )


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _integer(label: str, value: Any) -> int:
    if isinstance(value, bool) or isinstance(value, float):
        raise ScheduleError(f"{label} must be an integer, got {value!r}")
    if isinstance(value, int):
        return value
    text = str(value).strip()
    sign = ""
    digits = text
    if text[:1] in "+-":
        sign, digits = text[0], text[1:]
    if not digits.isdigit():
        raise ScheduleError(f"{label} must be an integer, got {value!r}")
    return int(sign + digits)


def _enabled(value: Any, *, label: str) -> bool:
    if isinstance(value, bool):
        return value
    token = str(value).strip().lower()
    if token in _OFF:
        return False
    if token in _ON:
        return True
    raise ScheduleError(f"{label} must be on or off, got {value!r}")


def _check_rules(schedule: Mapping[str, Any]) -> None:
    improvement = schedule.get("improvement")
    if improvement is not None and improvement != "strict":
        raise ScheduleError("improvement must be strict")
    ties = schedule.get("ties")
    if ties is not None and ties != "keep_earlier":
        raise ScheduleError("ties keep the earlier checkpoint")
    if "restore_best" in schedule and schedule.get("restore_best") is not True:
        raise ScheduleError("restore_best stays on")


def _finish(
    *,
    max_epochs: int,
    early_stopping: bool,
    patience: int | None,
    minimum_epochs: int | None,
    source: str,
) -> TrainingSchedule:
    if max_epochs < 1:
        raise ScheduleError(f"{TRAIN_EPOCHS_ENV} must be >= 1, got {max_epochs}")
    if early_stopping:
        if patience is None or minimum_epochs is None:
            raise ScheduleError("early stopping requires patience and minimum epochs")
        if patience < 0:
            raise ScheduleError(f"{EARLY_STOP_PATIENCE_ENV} must be >= 0, got {patience}")
        if minimum_epochs < 1:
            raise ScheduleError(f"{EARLY_STOP_MIN_EPOCHS_ENV} must be >= 1, got {minimum_epochs}")
        if minimum_epochs > max_epochs:
            raise ScheduleError(
                f"{EARLY_STOP_MIN_EPOCHS_ENV}={minimum_epochs} exceeds "
                f"{TRAIN_EPOCHS_ENV}={max_epochs}"
            )
    elif patience is not None or minimum_epochs is not None:
        raise ScheduleError("patience requires early stopping")
    return TrainingSchedule(
        max_epochs=max_epochs,
        early_stopping=early_stopping,
        patience=patience,
        minimum_epochs=minimum_epochs,
        improvement="strict",
        ties="keep_earlier",
        restore_best=True,
        source=source,
    )


def _schedule_body(preregistered: Mapping[str, Any]) -> Mapping[str, Any]:
    if "training_schedule" in preregistered:
        body = preregistered["training_schedule"]
        if not isinstance(body, Mapping):
            raise ScheduleError("training_schedule must be an object")
        return body
    if "max_epochs" in preregistered or TRAIN_EPOCHS_ENV in preregistered:
        return preregistered
    if "control_schedule" in preregistered or "candidate_schedule" in preregistered:
        arm = preregistered.get("schedule_arm")
        if arm == "control":
            return preregistered["control_schedule"]
        if arm == "candidate":
            return preregistered["candidate_schedule"]
        raise ScheduleError("preregistration names two schedules; set schedule_arm")
    raise ScheduleError("preregistration has no training schedule")


def parse_preregistered_schedule(preregistered: Mapping[str, Any]) -> TrainingSchedule:
    """One explicit schedule. It replaces the SELECT-006 candidate default."""
    body = _schedule_body(preregistered)
    _check_rules(body)
    if TRAIN_EPOCHS_ENV in body or EARLY_STOP_ENV in body:
        return _from_environment(body, source=SOURCE_PREREGISTERED)
    if "max_epochs" not in body:
        raise ScheduleError("preregistered schedule needs max_epochs")
    max_epochs = _integer("max_epochs", body["max_epochs"])
    if "early_stopping" in body:
        enabled = _enabled(body["early_stopping"], label="early_stopping")
    else:
        enabled = "early_stopping_patience" in body or "minimum_epochs" in body
    patience = None
    minimum = None
    if enabled:
        if "early_stopping_patience" not in body or "minimum_epochs" not in body:
            raise ScheduleError("early stopping requires patience and minimum epochs")
        patience = _integer("early_stopping_patience", body["early_stopping_patience"])
        minimum = _integer("minimum_epochs", body["minimum_epochs"])
    return _finish(
        max_epochs=max_epochs,
        early_stopping=enabled,
        patience=patience,
        minimum_epochs=minimum,
        source=SOURCE_PREREGISTERED,
    )


def _from_environment(env: Mapping[str, Any], *, source: str) -> TrainingSchedule:
    epochs_raw = env.get(TRAIN_EPOCHS_ENV)
    max_epochs = HISTORICAL_MAX_EPOCHS if _blank(epochs_raw) else _integer(TRAIN_EPOCHS_ENV, epochs_raw)
    early_raw = env.get(EARLY_STOP_ENV)
    patience_raw = env.get(EARLY_STOP_PATIENCE_ENV)
    minimum_raw = env.get(EARLY_STOP_MIN_EPOCHS_ENV)
    enabled = False if _blank(early_raw) else _enabled(early_raw, label=EARLY_STOP_ENV)
    if not enabled and (not _blank(patience_raw) or not _blank(minimum_raw)):
        raise ScheduleError("patience requires early stopping")
    patience = None if not enabled else _integer(EARLY_STOP_PATIENCE_ENV, patience_raw)
    minimum = None if not enabled else _integer(EARLY_STOP_MIN_EPOCHS_ENV, minimum_raw)
    return _finish(
        max_epochs=max_epochs,
        early_stopping=enabled,
        patience=patience,
        minimum_epochs=minimum,
        source=source,
    )


def schedule_is_explicit(env: Mapping[str, Any]) -> bool:
    return any(not _blank(env.get(key)) for key in SCHEDULE_ENV_KEYS)


def _same_schedule(left: TrainingSchedule, right: TrainingSchedule) -> bool:
    return (
        left.max_epochs == right.max_epochs
        and left.early_stopping == right.early_stopping
        and left.patience == right.patience
        and left.minimum_epochs == right.minimum_epochs
    )


def resolve_training_schedule(
    *,
    select_metric: str,
    environ: Mapping[str, str] | None = None,
    preregistered: Mapping[str, Any] | None = None,
) -> TrainingSchedule:
    """Default, historical, or the preregistered override.

    An explicit environment and a preregistered mapping must describe the
    same epochs and early-stop bounds. Neither one is filled in from the
    SELECT-006 candidate default.
    """
    env = os.environ if environ is None else environ
    explicit = schedule_is_explicit(env)
    if preregistered is not None and explicit:
        declared = parse_preregistered_schedule(preregistered)
        from_env = _from_environment(env, source=SOURCE_PREREGISTERED)
        if not _same_schedule(declared, from_env):
            raise ScheduleError("preregistered schedule does not match the process environment")
        return declared
    if preregistered is not None:
        return parse_preregistered_schedule(preregistered)
    if explicit:
        return _from_environment(env, source=SOURCE_PREREGISTERED)
    if select_metric == SELECT_METRIC_CLASSIFY:
        return select_006_candidate_schedule()
    return _finish(
        max_epochs=HISTORICAL_MAX_EPOCHS,
        early_stopping=False,
        patience=None,
        minimum_epochs=None,
        source=SOURCE_HISTORICAL,
    )


def environment_for_schedule(schedule: TrainingSchedule) -> dict[str, str]:
    """Environment overlay a launcher exports for a preregistered schedule."""
    overlay = {TRAIN_EPOCHS_ENV: str(schedule.max_epochs)}
    if schedule.early_stopping:
        overlay[EARLY_STOP_ENV] = "1"
        overlay[EARLY_STOP_PATIENCE_ENV] = str(schedule.patience)
        overlay[EARLY_STOP_MIN_EPOCHS_ENV] = str(schedule.minimum_epochs)
        return overlay
    overlay[EARLY_STOP_ENV] = "0"
    return overlay


def install_default_schedule(environ: MutableMapping[str, str] | None = None) -> None:
    """Publish the candidate default without replacing an explicit schedule."""
    env: MutableMapping[str, str]
    if environ is None:
        env = os.environ
    else:
        env = environ
    if schedule_is_explicit(env):
        return
    default = select_006_candidate_schedule()
    overlay = environment_for_schedule(default)
    for key, value in overlay.items():
        env.setdefault(key, value)
