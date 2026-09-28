"""Direction evaluation compares frozen HIGH and SECONDARY residuals only."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from hyperlexical.residual_model_resolved_replay_v1 import (
    INVERTED,
    NO_SEPARATION,
    SUPPORTED,
    direction_result,
    pair_comparison,
)
from hyperlexical.residual_threshold_v2_direction import (
    ANALYSIS_SCOPE,
    CONFOUND_NEXT,
    EXPECTED_JOIN,
    EXPECTED_MEASUREMENT,
    FROZEN_READY,
    UNCERTAINTY,
    compare_direction,
    ready_residuals,
)


def _row(index: int, label: str, status: str, score: str | None) -> dict:
    return {
        "calibration_row_id": index,
        "operator_label": label,
        "pos": "noun",
        "pwn30_synset": f"noun:{index:08d}",
        "residual_score": score,
        "row_id": f"row-{index}",
        "row_resolution_status": status,
        "surface": f"surface {index}",
    }


def _panel(high: list[str], secondary: list[str]) -> list[dict]:
    rows = []
    index = 1
    plan = [
        ("HIGH", "RESIDUAL_READY", high),
        ("SECONDARY", "RESIDUAL_READY", secondary),
        ("REJECT", "RESIDUAL_READY", ["0.0100000000"] * 24),
        ("QUARANTINE", "RESIDUAL_READY", ["0.0200000000"]),
        ("HIGH", "UNKNOWN", [None] * 31),
        ("SECONDARY", "UNKNOWN", [None] * 60),
        ("REJECT", "UNKNOWN", [None] * 47),
        ("QUARANTINE", "UNKNOWN", [None] * 2),
    ]
    for label, status, scores in plan:
        for score in scores:
            rows.append(_row(index, label, status, score))
            index += 1
    assert len(rows) == 200
    return rows


def test_ready_residuals_copy_the_frozen_strings_and_leave_reject_out() -> None:
    high = ["0.8100000000"] * 13
    secondary = ["0.2200000000"] * 22
    rows = _panel(high, secondary)
    ready = ready_residuals(rows, expect_frozen_counts=True)
    assert ready["HIGH"] == high
    assert ready["SECONDARY"] == secondary
    assert len(ready["REJECT"]) == FROZEN_READY["REJECT"]
    assert len(ready["QUARANTINE"]) == FROZEN_READY["QUARANTINE"]
    assert ready["HIGH"][0] == "0.8100000000"


def test_supported_direction_uses_the_frozen_rule() -> None:
    high = ["0.8000000000", "0.9000000000"]
    secondary = ["0.1000000000", "0.2000000000"]
    report = compare_direction(high, secondary)
    assert report["direction_result"] == direction_result(pair_comparison(high, secondary))
    assert report["direction_result"] == SUPPORTED
    assert report["high_larger_pairs"] == 4
    assert report["secondary_larger_pairs"] == 0
    assert report["ties"] == 0
    assert report["high_distribution"]["count"] == 2
    assert report["secondary_distribution"]["count"] == 2


def test_inverted_direction_is_preserved() -> None:
    high = ["0.1000000000", "0.2000000000"]
    secondary = ["0.8000000000", "0.9000000000"]
    report = compare_direction(high, secondary)
    assert report["direction_result"] == INVERTED
    assert report["secondary_larger_pairs"] == 4
    assert report["high_larger_pairs"] == 0


def test_no_directional_separation_is_preserved() -> None:
    high = ["0.5000000000"]
    secondary = ["0.5000000000"]
    report = compare_direction(high, secondary)
    assert report["direction_result"] == NO_SEPARATION
    assert report["ties"] == 1
    frozen = pair_comparison(high, secondary)
    assert report["mean_difference"] == frozen["mean_difference"]
    assert report["roc_auc"] == frozen["auc"] == "0.500000"


def test_ready_count_drift_is_refused() -> None:
    rows = _panel(["0.8100000000"] * 13, ["0.2200000000"] * 22)
    rows[0]["operator_label"] = "SECONDARY"
    with pytest.raises(SystemExit):
        ready_residuals(rows, expect_frozen_counts=True)


def test_direction_module_stops_before_confound_and_threshold_search() -> None:
    path = Path(inspect.getsourcefile(compare_direction))
    text = path.read_text(encoding="utf-8")
    assert EXPECTED_JOIN in text
    assert EXPECTED_MEASUREMENT in text
    assert UNCERTAINTY in text
    assert ANALYSIS_SCOPE in text
    assert CONFOUND_NEXT in text
    assert "bootstrap_intervals(" not in text
    assert "select_threshold(" not in text
    assert "_candidate_thresholds(" not in text
    assert "_confound(" not in text
    assert "extreme_driven" not in text
    source = inspect.getsource(compare_direction)
    assert "pair_comparison(high_scores, secondary_scores)" in source
    assert "REJECT" not in source
