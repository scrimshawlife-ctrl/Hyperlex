"""Default-off early stop for the classify training loop. No sleeps."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hyperlexical.classify_metrics import SELECT_METRIC_CLASSIFY, SELECT_METRIC_UNBIND
from hyperlexical.loop import (
    EARLY_STOP_ENV,
    EARLY_STOP_MIN_EPOCHS_ENV,
    EARLY_STOP_PATIENCE_ENV,
    STOP_REASON_EARLY_STOPPING,
    STOP_REASON_MAX_EPOCHS,
    early_stop_break,
    epoch_timing_fields,
    monotonic_seconds,
    note_strict_improvement,
    resolve_early_stop_config,
    round_seconds,
)
import hyperlexical.loop as loop

# Best classify score at epoch 3. Later values never strictly exceed it.
CANDIDATE = [0.50, 0.40, 0.45, 0.70, 0.55, 0.60, 0.58, 0.69, 0.10, 0.11, 0.12, 0.13]


def _enable(monkeypatch, *, patience="4", minimum_epochs="4"):
    monkeypatch.setenv(EARLY_STOP_ENV, "1")
    monkeypatch.setenv(EARLY_STOP_PATIENCE_ENV, patience)
    monkeypatch.setenv(EARLY_STOP_MIN_EPOCHS_ENV, minimum_epochs)


def _disable(monkeypatch):
    monkeypatch.delenv(EARLY_STOP_ENV, raising=False)
    monkeypatch.delenv(EARLY_STOP_PATIENCE_ENV, raising=False)
    monkeypatch.delenv(EARLY_STOP_MIN_EPOCHS_ENV, raising=False)


def run_classify_schedule(
    scores: list[float],
    *,
    max_epochs: int,
    enabled: bool,
    patience: int | None = None,
    minimum_epochs: int | None = None,
) -> dict[str, object]:
    """Same order as the trainer: score, strict improvement, then stop check."""
    best_value = float("-inf")
    best_epoch = None
    restored_epoch = None
    stop_reason = STOP_REASON_MAX_EPOCHS
    scored = 0
    last_epoch = None
    for ep in range(max_epochs):
        if ep >= len(scores):
            raise AssertionError(f"missing score for epoch {ep}")
        best_value, best_epoch, improved = note_strict_improvement(
            best_value, best_epoch, scores[ep], ep
        )
        if improved:
            restored_epoch = ep
        scored = ep + 1
        last_epoch = ep
        if early_stop_break(
            enabled=enabled,
            epoch_index=ep,
            best_epoch=best_epoch,
            epochs_scored=scored,
            minimum_epochs=minimum_epochs,
            patience=patience,
            max_epochs=max_epochs,
        ):
            stop_reason = STOP_REASON_EARLY_STOPPING
            break
    return {
        "stop_reason": stop_reason,
        "epochs_scored": scored,
        "last_epoch": last_epoch,
        "best_epoch": best_epoch,
        "restored_epoch": restored_epoch,
        "best_value": best_value,
    }


def test_default_off_runs_the_full_schedule(monkeypatch):
    _disable(monkeypatch)
    monkeypatch.setenv("HYPERLEX_TRAIN_EPOCHS", "12")
    monkeypatch.setenv(EARLY_STOP_PATIENCE_ENV, "-1")
    cfg = resolve_early_stop_config(max_epochs=12, select_metric=SELECT_METRIC_CLASSIFY)
    assert cfg.enabled is False
    result = run_classify_schedule(
        CANDIDATE,
        max_epochs=12,
        enabled=cfg.enabled,
        patience=4,
        minimum_epochs=4,
    )
    assert result["epochs_scored"] == 12
    assert result["last_epoch"] == 11
    assert result["stop_reason"] == STOP_REASON_MAX_EPOCHS
    assert result["best_epoch"] == 3


def test_train_epochs_alone_does_not_enable_early_stop(monkeypatch):
    _disable(monkeypatch)
    monkeypatch.setenv("HYPERLEX_TRAIN_EPOCHS", "12")
    cfg = resolve_early_stop_config(max_epochs=12, select_metric=SELECT_METRIC_UNBIND)
    assert cfg.enabled is False
    assert cfg.patience is None
    assert cfg.minimum_epochs is None


def test_minimum_epochs_block_an_earlier_patience_fire():
    scores = [0.90, 0.10, 0.10, 0.10, 0.10, 0.10]
    result = run_classify_schedule(
        scores,
        max_epochs=6,
        enabled=True,
        patience=1,
        minimum_epochs=4,
    )
    assert result["best_epoch"] == 0
    assert result["last_epoch"] == 3
    assert result["epochs_scored"] == 4
    assert result["stop_reason"] == STOP_REASON_EARLY_STOPPING


def test_best_at_epoch_3_stops_after_epoch_7_with_patience_4():
    result = run_classify_schedule(
        CANDIDATE,
        max_epochs=12,
        enabled=True,
        patience=4,
        minimum_epochs=4,
    )
    assert result["best_epoch"] == 3
    assert result["last_epoch"] == 7
    assert result["epochs_scored"] == 8
    assert result["stop_reason"] == STOP_REASON_EARLY_STOPPING
    assert result["restored_epoch"] == 3


def test_strict_improvement_resets_patience():
    scores = list(CANDIDATE)
    scores[5] = 0.80
    result = run_classify_schedule(
        scores,
        max_epochs=12,
        enabled=True,
        patience=4,
        minimum_epochs=4,
    )
    assert result["best_epoch"] == 5
    assert result["last_epoch"] == 9
    assert result["epochs_scored"] == 10
    assert result["stop_reason"] == STOP_REASON_EARLY_STOPPING


def test_ties_keep_the_earlier_checkpoint_and_consume_patience():
    scores = list(CANDIDATE)
    scores[7] = scores[3]
    assert scores[7] == scores[3]
    result = run_classify_schedule(
        scores,
        max_epochs=12,
        enabled=True,
        patience=4,
        minimum_epochs=4,
    )
    assert result["best_epoch"] == 3
    assert result["restored_epoch"] == 3
    assert result["last_epoch"] == 7
    assert result["epochs_scored"] == 8
    assert result["best_value"] == scores[3]
    tied = [0.50, 0.50]
    short = run_classify_schedule(
        tied,
        max_epochs=4,
        enabled=True,
        patience=1,
        minimum_epochs=1,
    )
    assert short["best_epoch"] == 0
    assert short["restored_epoch"] == 0
    assert short["last_epoch"] == 1
    assert short["stop_reason"] == STOP_REASON_EARLY_STOPPING


def test_improvement_on_the_would_be_stopping_epoch_prevents_stopping():
    scores = list(CANDIDATE) + [0.10, 0.10, 0.10, 0.10]
    scores[7] = 0.71
    stopped_without = run_classify_schedule(
        CANDIDATE,
        max_epochs=16,
        enabled=True,
        patience=4,
        minimum_epochs=4,
    )
    assert stopped_without["last_epoch"] == 7
    result = run_classify_schedule(
        scores,
        max_epochs=16,
        enabled=True,
        patience=4,
        minimum_epochs=4,
    )
    assert result["best_epoch"] == 7
    assert result["restored_epoch"] == 7
    assert result["last_epoch"] == 11
    assert result["epochs_scored"] == 12
    assert result["stop_reason"] == STOP_REASON_EARLY_STOPPING


def test_max_epoch_cap_wins_when_reached_first():
    early = run_classify_schedule(
        CANDIDATE,
        max_epochs=6,
        enabled=True,
        patience=4,
        minimum_epochs=4,
    )
    assert early["epochs_scored"] == 6
    assert early["last_epoch"] == 5
    assert early["best_epoch"] == 3
    assert early["stop_reason"] == STOP_REASON_MAX_EPOCHS
    # Patience would also be true on the final configured epoch. The cap wins.
    on_the_cap = run_classify_schedule(
        CANDIDATE,
        max_epochs=8,
        enabled=True,
        patience=4,
        minimum_epochs=4,
    )
    assert on_the_cap["last_epoch"] == 7
    assert on_the_cap["epochs_scored"] == 8
    assert on_the_cap["stop_reason"] == STOP_REASON_MAX_EPOCHS
    assert on_the_cap["restored_epoch"] == 3


def test_best_checkpoint_restored_after_early_stop():
    result = run_classify_schedule(
        CANDIDATE,
        max_epochs=12,
        enabled=True,
        patience=4,
        minimum_epochs=4,
    )
    assert result["stop_reason"] == STOP_REASON_EARLY_STOPPING
    assert result["restored_epoch"] == result["best_epoch"] == 3
    assert result["restored_epoch"] != result["last_epoch"]
    src = Path(loop.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_loop")
    break_line = None
    restore_line = None
    for node in ast.walk(fn):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "early_stop_break":
            break_line = node.lineno
        if isinstance(node, ast.BoolOp):
            text = ast.get_source_segment(src, node) or ""
            if "best_state is not None" in text:
                restore_line = node.lineno
    assert break_line is not None and restore_line is not None
    assert break_line < restore_line


@pytest.mark.parametrize(
    ("env", "metric", "match"),
    [
        ({"patience": "-1", "minimum": "4"}, SELECT_METRIC_CLASSIFY, "PATIENCE"),
        ({"patience": "4", "minimum": "0"}, SELECT_METRIC_CLASSIFY, "MIN_EPOCHS"),
        ({"patience": "4", "minimum": "-2"}, SELECT_METRIC_CLASSIFY, "MIN_EPOCHS"),
        ({"patience": "4", "minimum": "13"}, SELECT_METRIC_CLASSIFY, "exceeds"),
        ({"patience": "4.5", "minimum": "4"}, SELECT_METRIC_CLASSIFY, "integer"),
        ({"patience": "4", "minimum": "nope"}, SELECT_METRIC_CLASSIFY, "integer"),
        ({"patience": None, "minimum": "4"}, SELECT_METRIC_CLASSIFY, "required"),
        ({"patience": "4", "minimum": None}, SELECT_METRIC_CLASSIFY, "required"),
        ({"patience": "4", "minimum": "4"}, SELECT_METRIC_UNBIND, "classify_macro_f1_nonnone"),
    ],
)
def test_invalid_configuration_fails_before_optimizer(monkeypatch, env, metric, match):
    monkeypatch.setenv(EARLY_STOP_ENV, "1")
    if env["patience"] is None:
        monkeypatch.delenv(EARLY_STOP_PATIENCE_ENV, raising=False)
    else:
        monkeypatch.setenv(EARLY_STOP_PATIENCE_ENV, env["patience"])
    if env["minimum"] is None:
        monkeypatch.delenv(EARLY_STOP_MIN_EPOCHS_ENV, raising=False)
    else:
        monkeypatch.setenv(EARLY_STOP_MIN_EPOCHS_ENV, env["minimum"])
    constructed: list[object] = []

    def adamw(*args, **kwargs):
        constructed.append(args)
        raise AssertionError("optimizer constructed")

    with pytest.raises(ValueError, match=match):
        resolve_early_stop_config(max_epochs=12, select_metric=metric)
        adamw([object()], lr=2e-5)
    assert constructed == []

    src = Path(loop.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_loop")
    resolve_line = None
    adam_line = None
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        if name == "resolve_early_stop_config":
            resolve_line = node.lineno
        if name == "AdamW":
            adam_line = node.lineno
    assert resolve_line is not None and adam_line is not None
    assert resolve_line < adam_line


def test_unknown_early_stop_token_is_rejected(monkeypatch):
    monkeypatch.setenv(EARLY_STOP_ENV, "maybe")
    with pytest.raises(ValueError, match="HYPERLEX_EARLY_STOP"):
        resolve_early_stop_config(max_epochs=12, select_metric=SELECT_METRIC_CLASSIFY)


def test_explicit_off_runs_full_schedule(monkeypatch):
    monkeypatch.setenv(EARLY_STOP_ENV, "off")
    monkeypatch.setenv(EARLY_STOP_PATIENCE_ENV, "1")
    monkeypatch.setenv(EARLY_STOP_MIN_EPOCHS_ENV, "1")
    cfg = resolve_early_stop_config(max_epochs=12, select_metric=SELECT_METRIC_CLASSIFY)
    assert cfg.enabled is False
    result = run_classify_schedule(
        CANDIDATE,
        max_epochs=cfg.max_epochs,
        enabled=cfg.enabled,
    )
    assert result["epochs_scored"] == 12
    assert result["stop_reason"] == STOP_REASON_MAX_EPOCHS


def test_wallclock_fields_are_nonnegative_and_cumulative(monkeypatch):
    ticks = iter([0.0, 1.0, 1.25, 1.25, 2.50, 2.50, 2.75])

    def clock() -> float:
        return next(ticks)

    monkeypatch.setattr(loop, "monotonic_seconds", clock)
    training_started = loop.monotonic_seconds()
    rows = []
    for epoch in range(3):
        epoch_started = loop.monotonic_seconds()
        row = {
            "epoch": epoch,
            "unbind_exact": 0.0,
            "saved_best": False,
            "classify_acc": 0.5,
        }
        row.update(
            epoch_timing_fields(
                epoch_started=epoch_started,
                epoch_ended=loop.monotonic_seconds(),
                training_started=training_started,
            )
        )
        rows.append(row)
    elapsed = [row["training_elapsed_seconds"] for row in rows]
    assert elapsed == sorted(elapsed)
    assert all(later >= earlier for earlier, later in zip(elapsed, elapsed[1:]))
    for row in rows:
        assert row["epoch_wallclock_seconds"] >= 0
        assert row["training_elapsed_seconds"] >= 0
        assert "epoch" in row and "saved_best" in row
    assert rows[0]["epoch_wallclock_seconds"] == 0.25
    assert rows[1]["epoch_wallclock_seconds"] == 1.25
    assert rows[2]["epoch_wallclock_seconds"] == 0.25
    assert rows[-1]["training_elapsed_seconds"] == 2.75
    assert round_seconds(1.23456789) == round(1.23456789, 6)
    assert inspect.signature(epoch_timing_fields).parameters.keys() >= {
        "epoch_started",
        "epoch_ended",
        "training_started",
    }


def test_wallclock_values_do_not_affect_selection(monkeypatch):
    def boom() -> float:
        raise AssertionError("selection read the clock")

    monkeypatch.setattr(loop, "monotonic_seconds", boom)
    first = run_classify_schedule(
        CANDIDATE,
        max_epochs=12,
        enabled=True,
        patience=4,
        minimum_epochs=4,
    )
    second = run_classify_schedule(
        CANDIDATE,
        max_epochs=12,
        enabled=True,
        patience=4,
        minimum_epochs=4,
    )
    assert first == second
    assert first["best_epoch"] == 3
    assert "epoch_wallclock_seconds" not in inspect.signature(note_strict_improvement).parameters
    assert "training_elapsed_seconds" not in inspect.signature(early_stop_break).parameters
    stamped = epoch_timing_fields(epoch_started=0.0, epoch_ended=50.0, training_started=0.0)
    assert stamped["training_elapsed_seconds"] == 50.0
    assert first["best_epoch"] == 3


def test_disabled_selection_keeps_strict_increase_and_earlier_ties():
    scores = [0.20, 0.50, 0.50, 0.40, 0.80, 0.80]
    best_value = float("-inf")
    best_epoch = None
    improved_flags = []
    for epoch, score in enumerate(scores):
        best_value, best_epoch, improved = note_strict_improvement(
            best_value, best_epoch, score, epoch
        )
        improved_flags.append(improved)
    assert improved_flags == [True, True, False, False, True, False]
    assert best_epoch == 4
    result = run_classify_schedule(
        scores,
        max_epochs=len(scores),
        enabled=False,
    )
    assert result["epochs_scored"] == len(scores)
    assert result["stop_reason"] == STOP_REASON_MAX_EPOCHS
    assert result["best_epoch"] == 4
    assert result["restored_epoch"] == 4


def test_completion_receipt_records_only_loop_stop_reasons():
    src = Path(loop.__file__).read_text(encoding="utf-8")
    assert '"stop_reason": stop_reason' in src
    assert '"training_elapsed_seconds": training_elapsed_seconds' in src
    tree = ast.parse(src)
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_loop")
    assigned: list[str] = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "stop_reason":
                assigned.append(ast.get_source_segment(src, node.value) or "")
    assert assigned == ["STOP_REASON_MAX_EPOCHS", "STOP_REASON_EARLY_STOPPING"]
    assert STOP_REASON_MAX_EPOCHS == "max_epochs"
    assert STOP_REASON_EARLY_STOPPING == "early_stopping"
    assert "stop_reason" not in inspect.signature(monotonic_seconds).parameters
