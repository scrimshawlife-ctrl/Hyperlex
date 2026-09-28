"""Calibration completion keeps the frozen confound stop and precision gates."""

from __future__ import annotations

import inspect
from decimal import Decimal
from pathlib import Path

from hyperlexical.residual_threshold_v1 import (
    MIN_PREDICTED_YES,
    PRECISION_FLOOR,
    WILSON_LOWER_FLOOR,
    _candidate_thresholds,
    _comparison,
    _ready_rows,
)
from hyperlexical.residual_threshold_v2_calibration import MEASUREMENT_NEXT
from hyperlexical.residual_threshold_v2_completion import (
    COMPLETION_SEARCH_PATH,
    EXECUTION_SEARCH,
    EXPECTED_EXECUTION_SEARCH,
    EXPECTED_MEASUREMENT,
    TRAINING_BLOCKED,
    TRAINING_PENDING,
    confound_stop,
    itemized_gate_counts,
)


def _row(bucket: str, residual: str, pos: str = "noun", tier3: bool = False) -> dict:
    return {
        "development_row": False,
        "operator_bucket": bucket,
        "pos": pos,
        "residual_score": residual,
        "score_status": "SCORED",
        "uses_tier3": tier3,
    }


def test_only_the_three_frozen_flags_stop_confound_review() -> None:
    assert confound_stop(
        {"extreme_driven": False, "pos_partitioned": False, "tier3_concentrated": False}
    ) is False
    assert confound_stop(
        {"extreme_driven": True, "pos_partitioned": False, "tier3_concentrated": False}
    ) is True
    assert confound_stop(
        {"extreme_driven": False, "pos_partitioned": True, "tier3_concentrated": False}
    ) is True
    assert confound_stop(
        {"extreme_driven": False, "pos_partitioned": False, "tier3_concentrated": True}
    ) is True
    source = inspect.getsource(confound_stop)
    assert "spearman" not in source
    assert "token_count" not in source


def test_itemized_counts_use_the_frozen_floors() -> None:
    assert MIN_PREDICTED_YES == 8
    assert PRECISION_FLOOR == Decimal("0.80")
    assert WILSON_LOWER_FLOOR == Decimal("0.50")
    rows = [_row("HIGH", f"0.{index:010d}") for index in range(13)]
    rows.extend(_row("SECONDARY", f"0.{index:010d}") for index in range(13, 35))
    rows.extend(_row("REJECT", "0.9000000000") for _ in range(2))
    rows.append(_row("QUARANTINE", "0.9500000000"))
    ready = _ready_rows(rows)
    comparison = _comparison(ready)
    counts = itemized_gate_counts(ready, comparison, _candidate_thresholds(ready))
    assert counts["candidates"] == len(_candidate_thresholds(ready))
    assert counts["reject_veto"] < counts["candidates"]
    assert counts["quarantine_veto"] < counts["candidates"]
    assert counts["all_gates"] <= counts["leave_one_out"]


def test_completion_module_does_not_rescore_or_open_measurement_rows() -> None:
    path = Path(inspect.getsourcefile(confound_stop))
    text = path.read_text(encoding="utf-8")
    assert EXPECTED_MEASUREMENT in text
    assert EXPECTED_EXECUTION_SEARCH in text
    assert MEASUREMENT_NEXT == "THRESHOLD_V2_MEASUREMENT_EXECUTION_AUTHORIZATION"
    assert TRAINING_BLOCKED in text
    assert TRAINING_PENDING in text
    assert "encode_needed(" not in text
    assert "load_encoder(" not in text
    assert "bootstrap_intervals(" not in text
    assert "GlossBERT(" not in text
    assert COMPLETION_SEARCH_PATH.name != EXECUTION_SEARCH.name
    assert "MEASUREMENT_MANIFEST.read_text" not in text
    source = inspect.getsource(path and __import__("hyperlexical.residual_threshold_v2_completion", fromlist=["complete"]).complete)
    assert source.index("if stopped:") < source.index("_search_body(")
