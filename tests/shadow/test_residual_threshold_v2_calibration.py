"""v2 calibration execution keeps the frozen gates and the sealed measurement surface."""

from __future__ import annotations

import inspect
from pathlib import Path

from hyperlexical.residual_threshold_v1 import MIN_CALIBRATION_HIGH, MIN_CALIBRATION_SECONDARY
import pytest

from hyperlexical.residual_threshold_v2_calibration import (
    EXPECTED_MEASUREMENT,
    _resolve,
    _score,
    lesk_tie_rows,
    support_passed,
)


def test_structural_ambiguity_does_not_enter_glossbert() -> None:
    rows = [
        {"constituent_index": 0, "resolution_method": "STRUCTURAL_EXACT", "resolution_status": "AMBIGUOUS"},
        {"constituent_index": 1, "resolution_method": "EXTENDED_LESK_V1", "resolution_status": "AMBIGUOUS"},
        {"constituent_index": 2, "resolution_method": "EXTENDED_LESK_V1", "resolution_status": "RESOLVED"},
        {"constituent_index": None, "resolution_method": "NONE", "resolution_status": None},
    ]
    kept = lesk_tie_rows(rows)
    assert [row["constituent_index"] for row in kept] == [1]
    with pytest.raises(SystemExit):
        lesk_tie_rows([{"constituent_index": 0, "resolution_method": "UNIQUE_LEMMA", "resolution_status": "AMBIGUOUS"}])


def test_support_floors_are_unchanged() -> None:
    assert MIN_CALIBRATION_HIGH == 12
    assert MIN_CALIBRATION_SECONDARY == 8
    assert support_passed(12, 8) is True
    assert support_passed(11, 8) is False
    assert support_passed(12, 7) is False


def test_execution_module_does_not_retune_or_open_measurement() -> None:
    path = Path(inspect.getsourcefile(support_passed))
    text = path.read_text(encoding="utf-8")
    assert EXPECTED_MEASUREMENT in text
    assert "select_threshold(" in text
    assert "0.672078" not in text
    assert "0.4040327275" not in text
    assert "semantic_noncompositional = YES" not in text
    assert "semantic_noncompositional = NO" not in text
    assert "_label_index" not in inspect.getsource(_resolve)
    assert "_label_index" not in inspect.getsource(_score)
    assert "MEASUREMENT_MANIFEST" not in inspect.getsource(_resolve)
    assert "MEASUREMENT_MANIFEST" not in inspect.getsource(_score)
