"""v2 preregisters a larger blind draw and does not relax v1."""

from __future__ import annotations

import inspect
from decimal import Decimal
from pathlib import Path

from hyperlexical.residual_threshold_v1 import (
    MIN_CALIBRATION_HIGH,
    MIN_CALIBRATION_SECONDARY,
    PRECISION_FLOOR,
)
from hyperlexical.residual_threshold_v2 import (
    CONSERVATIVE_READINESS,
    REQUIRED_TARGET_READY,
    V1_EXECUTION_STATE,
    calibration_draw_size,
    measurement_draw_size,
    quota_from_readiness,
)


def test_quota_is_the_readiness_formula() -> None:
    assert MIN_CALIBRATION_HIGH == 12
    assert MIN_CALIBRATION_SECONDARY == 8
    assert REQUIRED_TARGET_READY == 20
    assert CONSERVATIVE_READINESS == Decimal("0.20")
    assert CONSERVATIVE_READINESS < (Decimal(6) / Decimal(27))
    assert quota_from_readiness() == 200
    assert calibration_draw_size() == 200
    assert measurement_draw_size() == 200
    assert PRECISION_FLOOR == Decimal("0.80")


def test_historical_rates_do_not_enter_the_formula() -> None:
    source = inspect.getsource(quota_from_readiness)
    assert "73" not in source
    assert "225" not in source
    assert "6" not in source


def test_preregistration_does_not_draw_or_refit() -> None:
    text = Path(inspect.getsourcefile(quota_from_readiness)).read_text(encoding="utf-8")
    assert "select_threshold(" not in text
    assert "0.672078" not in text
    assert V1_EXECUTION_STATE == "CALIBRATION_INSUFFICIENT_SUPPORT"
    freeze = Path(inspect.getsourcefile(quota_from_readiness)).with_name("residual_threshold_v2_freeze.py").read_text(encoding="utf-8")
    assert "select_threshold(" not in freeze
