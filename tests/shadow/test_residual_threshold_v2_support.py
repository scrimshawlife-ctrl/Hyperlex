"""Support reassessment counts frozen ready labels and does not search a threshold."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from hyperlexical.residual_threshold_v1 import MIN_CALIBRATION_HIGH, MIN_CALIBRATION_SECONDARY
from hyperlexical.residual_threshold_v2_support import (
    EXPECTED_MEASUREMENT,
    FAILED,
    FROZEN_READY,
    FROZEN_UNKNOWN,
    PASSED,
    gate_state,
    join_rows,
    support_inventory,
    support_passed,
)


def _label(index: int, bucket: str) -> dict:
    return {
        "calibration_row_id": index,
        "operator_evidence": "STRONG_IDIOM",
        "operator_label": bucket,
        "operator_note": "frozen note",
        "pos": "noun",
        "pwn30_synset": f"noun:{index:08d}",
        "review_status": "REVIEWED",
        "row_id": f"row-{index}",
        "surface": f"surface {index}",
    }


def _score(index: int, status: str) -> dict:
    row = {"row_id": f"row-{index}", "score_status": status}
    if status == "SCORED":
        row.update({
            "pos": "noun",
            "residual_score": "0.1000000000",
            "surface": f"surface {index}",
            "synset": f"noun:{index:08d}",
        })
    else:
        row["abstention_reason"] = "ambiguous_content_constituent"
    return row


def _population() -> tuple[list[dict], list[dict]]:
    labels = []
    scores = []
    index = 1
    plan = [("HIGH", "SCORED", 12), ("SECONDARY", "SCORED", 8), ("REJECT", "SCORED", 20), ("QUARANTINE", "SCORED", 20)]
    plan += [("HIGH", "UNKNOWN", 32), ("SECONDARY", "UNKNOWN", 74), ("REJECT", "UNKNOWN", 31), ("QUARANTINE", "UNKNOWN", 3)]
    for bucket, status, count in plan:
        for _ in range(count):
            labels.append(_label(index, bucket))
            scores.append(_score(index, status))
            index += 1
    assert index == 201
    return labels, scores


def test_floors_remain_twelve_and_eight() -> None:
    assert MIN_CALIBRATION_HIGH == 12
    assert MIN_CALIBRATION_SECONDARY == 8
    assert support_passed(12, 8) is True
    assert support_passed(11, 8) is False
    assert support_passed(12, 7) is False


def test_ready_labels_pass_without_reading_the_residual() -> None:
    labels, scores = _population()
    joined = join_rows(labels, scores)
    joined[0]["residual_score"] = "9.9999999999"
    inventory = support_inventory(joined)
    assert inventory["ready_rows"] == FROZEN_READY
    assert inventory["unknown_rows"] == FROZEN_UNKNOWN
    assert inventory["ready"] == {"HIGH": 12, "SECONDARY": 8, "REJECT": 20, "QUARANTINE": 20}
    assert gate_state(inventory) == PASSED


def test_short_ready_high_fails_and_unknown_labels_do_not_count() -> None:
    labels, scores = _population()
    scores[0]["score_status"] = "UNKNOWN"
    scores[0].pop("residual_score")
    scores[0]["abstention_reason"] = "unresolved_content_constituent"
    unknown_reject = 166
    assert labels[unknown_reject]["operator_label"] == "REJECT"
    assert scores[unknown_reject]["score_status"] == "UNKNOWN"
    scores[unknown_reject] = _score(unknown_reject + 1, "SCORED")
    scores[unknown_reject]["row_id"] = labels[unknown_reject]["row_id"]
    scores[unknown_reject]["surface"] = labels[unknown_reject]["surface"]
    scores[unknown_reject]["synset"] = labels[unknown_reject]["pwn30_synset"]
    joined = join_rows(labels, scores)
    inventory = support_inventory(joined)
    assert inventory["ready"]["HIGH"] == 11
    assert inventory["unknown_by_class"]["HIGH"] == 33
    assert inventory["ready_rows"] == FROZEN_READY
    assert gate_state(inventory) == FAILED


def test_join_keeps_the_frozen_label() -> None:
    label = _label(1, "QUARANTINE")
    score = _score(1, "UNKNOWN")
    joined = join_rows([label], [score])
    assert joined[0]["operator_label"] == "QUARANTINE"
    assert joined[0]["readiness"] == "UNKNOWN"
    assert joined[0]["residual_score"] is None


def test_support_module_does_not_search_or_open_measurement_work() -> None:
    path = Path(inspect.getsourcefile(support_inventory))
    text = path.read_text(encoding="utf-8")
    source = inspect.getsource(support_inventory)
    assert EXPECTED_MEASUREMENT in text
    assert "residual_score" not in source
    assert "_candidate_thresholds(" not in text
    assert "_confound(" not in text
    assert "select_threshold(" not in text
    assert "DIRECTION_NEXT" in text
    with pytest.raises(SystemExit):
        gate_state({"ready": {"HIGH": 12, "SECONDARY": 8}, "ready_rows": 59, "unknown_rows": 141})
