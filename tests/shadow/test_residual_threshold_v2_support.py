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
    JOIN_KEYS,
    PASSED,
    gate_state,
    join_rows,
    support_inventory,
    support_passed,
)


def _manifest(index: int) -> dict:
    return {
        "global_draw_order": index,
        "normalized_text_sha256": f"row-{index}",
        "pos": "noun",
        "pwn30_synset": f"noun:{index:08d}",
        "row_id": f"row-{index}",
        "surface": f"surface {index}",
    }


def _label(index: int, bucket: str) -> dict:
    return {
        "calibration_row_id": index,
        "operator_label": bucket,
        "pos": "noun",
        "pwn30_synset": f"noun:{index:08d}",
        "row_id": f"row-{index}",
        "surface": f"surface {index}",
    }


def _parent(index: int, status: str) -> dict:
    return {
        "pos": "noun",
        "row_id": f"row-{index}",
        "row_resolution_status": status,
        "surface": f"surface {index}",
        "synset": f"noun:{index:08d}",
    }


def _score(index: int, status: str) -> dict:
    row = {"row_id": f"row-{index}", "score_status": "SCORED" if status == "RESIDUAL_READY" else "UNKNOWN"}
    if status == "RESIDUAL_READY":
        row["residual_score"] = "0.1000000000"
    return row


def _population() -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    manifest, labels, parents, scores = [], [], [], []
    index = 1
    plan = [
        ("HIGH", "RESIDUAL_READY", 12),
        ("SECONDARY", "RESIDUAL_READY", 8),
        ("REJECT", "RESIDUAL_READY", 20),
        ("QUARANTINE", "RESIDUAL_READY", 20),
        ("HIGH", "UNKNOWN", 32),
        ("SECONDARY", "UNKNOWN", 74),
        ("REJECT", "UNKNOWN", 31),
        ("QUARANTINE", "UNKNOWN", 3),
    ]
    for bucket, status, count in plan:
        for _ in range(count):
            manifest.append(_manifest(index))
            labels.append(_label(index, bucket))
            parents.append(_parent(index, status))
            scores.append(_score(index, status))
            index += 1
    assert index == 201
    return manifest, labels, parents, scores


def test_floors_remain_twelve_and_eight() -> None:
    assert MIN_CALIBRATION_HIGH == 12
    assert MIN_CALIBRATION_SECONDARY == 8
    assert support_passed(12, 8) is True
    assert support_passed(11, 8) is False
    assert support_passed(12, 7) is False


def test_ready_labels_pass_without_reading_the_residual() -> None:
    manifest, labels, parents, scores = _population()
    joined = join_rows(manifest, labels, parents, scores)
    assert set(joined[0]) == JOIN_KEYS
    joined[0]["residual_score"] = "9.9999999999"
    inventory = support_inventory(joined)
    assert inventory["ready_rows"] == FROZEN_READY
    assert inventory["unknown_rows"] == FROZEN_UNKNOWN
    assert inventory["ready"] == {"HIGH": 12, "SECONDARY": 8, "REJECT": 20, "QUARANTINE": 20}
    assert inventory["ready_unresolved"] == 0
    assert gate_state(inventory) == PASSED


def test_short_ready_high_fails_and_unknown_labels_do_not_count() -> None:
    manifest, labels, parents, scores = _population()
    parents[0]["row_resolution_status"] = "UNKNOWN"
    scores[0] = _score(1, "UNKNOWN")
    unknown_reject = 166
    assert labels[unknown_reject]["operator_label"] == "REJECT"
    parents[unknown_reject]["row_resolution_status"] = "RESIDUAL_READY"
    scores[unknown_reject] = _score(unknown_reject + 1, "RESIDUAL_READY")
    scores[unknown_reject]["row_id"] = labels[unknown_reject]["row_id"]
    joined = join_rows(manifest, labels, parents, scores)
    inventory = support_inventory(joined)
    assert inventory["ready"]["HIGH"] == 11
    assert inventory["unknown_by_class"]["HIGH"] == 33
    assert inventory["ready_rows"] == FROZEN_READY
    assert gate_state(inventory) == FAILED


def test_join_keeps_the_frozen_label_and_null_residual() -> None:
    joined = join_rows(
        [_manifest(1)],
        [_label(1, "QUARANTINE")],
        [_parent(1, "UNKNOWN")],
        [_score(1, "UNKNOWN")],
    )
    assert joined[0]["operator_label"] == "QUARANTINE"
    assert joined[0]["row_resolution_status"] == "UNKNOWN"
    assert joined[0]["residual_score"] is None


def test_join_refuses_a_synset_mismatch() -> None:
    parent = _parent(1, "UNKNOWN")
    parent["synset"] = "noun:00000000"
    with pytest.raises(SystemExit):
        join_rows([_manifest(1)], [_label(1, "HIGH")], [parent], [_score(1, "UNKNOWN")])


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
    assert "MEASUREMENT_MANIFEST" not in inspect.getsource(join_rows)
    with pytest.raises(SystemExit):
        gate_state({"ready": {"HIGH": 12, "SECONDARY": 8}, "ready_rows": 59, "unknown_rows": 141})
