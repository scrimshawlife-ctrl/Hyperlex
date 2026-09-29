"""The v1 closure records a design mismatch and does not refit."""

from __future__ import annotations

import inspect
from pathlib import Path

from hyperlexical.residual_threshold_v1_design_closure import (
    DISPOSITION,
    DRAWN_ROWS,
    EXECUTION_STATE,
    FINDING,
    LABEL_CAUSE,
    RESIDUAL_READY,
    combined_ready_floor,
    threshold_eligibility,
)


def test_execution_outcome_stays_insufficient_support() -> None:
    assert EXECUTION_STATE == "CALIBRATION_INSUFFICIENT_SUPPORT"
    assert DISPOSITION == "CLOSED_CALIBRATION_DESIGN_INSUFFICIENT"
    assert FINDING == "CALIBRATION_DESIGN_SUPPORT_MISMATCH_CONFIRMED"
    assert LABEL_CAUSE == "NOVEL_SURFACE_UNLABELED"


def test_six_ready_rows_cannot_meet_the_frozen_floors() -> None:
    assert DRAWN_ROWS == 27
    assert RESIDUAL_READY == 6
    assert combined_ready_floor() == 20
    assert threshold_eligibility(6) == "mathematically_impossible"
    assert threshold_eligibility(20) == "not_ruled_out_by_ready_count"


def test_closure_does_not_select_or_redraw() -> None:
    text = Path(inspect.getsourcefile(threshold_eligibility)).read_text(encoding="utf-8")
    assert "select_threshold(" not in text
    assert "0.672078" not in text
    assert "0.4040327275" not in text
    assert "measurement_sample.jsonl" not in text
