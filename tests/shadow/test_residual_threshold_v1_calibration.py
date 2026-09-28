"""Guards for the one-draw calibration runner."""

from __future__ import annotations

import inspect
from pathlib import Path

from hyperlexical.residual_threshold_v1 import MIN_CALIBRATION_HIGH, MIN_CALIBRATION_SECONDARY
from hyperlexical.residual_threshold_v1_calibration import (
    DRAW_SEED,
    JSON_SCHEMA_DOCUMENT,
    MANIFEST_FIELDS,
    PER_CELL,
    SAMPLING_RULE_ID,
    draw_calibration,
)


def test_draw_rule_is_the_historical_prefix() -> None:
    assert SAMPLING_RULE_ID == "positional_stratified_hash_prefix_v1"
    assert PER_CELL == 2
    assert DRAW_SEED is None
    assert JSON_SCHEMA_DOCUMENT is None


def test_draw_does_not_read_operator_buckets() -> None:
    source = inspect.getsource(draw_calibration)
    assert "operator_bucket" not in source
    assert "select_threshold" not in source


def test_floors_come_from_the_frozen_procedure() -> None:
    assert MIN_CALIBRATION_HIGH == 12
    assert MIN_CALIBRATION_SECONDARY == 8
    text = Path(inspect.getsourcefile(draw_calibration)).read_text(encoding="utf-8")
    assert "0.672078" not in text
    assert "0.4040327275" not in text
    assert "measurement_sample.jsonl" not in text
    assert "def measurement_acceptance" not in text


def test_manifest_contract_has_no_label_field() -> None:
    assert "operator_bucket" not in MANIFEST_FIELDS
    assert "calibration_row_id" in MANIFEST_FIELDS
    assert "pwn30_synset" in MANIFEST_FIELDS
