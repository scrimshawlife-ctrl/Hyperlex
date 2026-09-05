"""Market signal connector + hyperstition feedback tests."""

from __future__ import annotations

import pytest

from hyperlex import (
    detect_memetic_patterns,
    extract_forecasts,
    settle,
    score_series,
    build_market_signal,
    build_forecast_pipeline,
    hyperstition_feedback_from_series,
)
from hyperlex.calibration.mapping import HYPERSTITION_STAGE_PROB
from hyperlex.connectors.hyperstition_feedback import map_hyperstition_with_override


def test_market_signal_packet_shape() -> None:
    result = detect_memetic_patterns("sharp steam revenge", ingest_source="mock")
    sig = build_market_signal(result)
    assert sig["schema"] == "hyperlex.market_signal.v1"
    assert sig["brier"] is None
    assert sig["actionable"] in {"MONITOR", "IGNORE", "ESCALATE"}
    assert sig["authority"] == "advisory"
    assert sig["packet_hash"]


def test_forecast_pipeline() -> None:
    result = detect_memetic_patterns("sharp steam revenge", ingest_source="mock")
    pipe = build_forecast_pipeline(result)
    assert pipe["schema"] == "hyperlex.forecast_pipeline.v1"
    assert pipe["n_forecasts"] >= 1
    assert pipe["market_signal"]["brier"] is None
    assert pipe["series_status"] == "NOT_COMPUTABLE"


def test_hyperstition_feedback_empty_not_computable() -> None:
    fb = hyperstition_feedback_from_series({"status": "NOT_COMPUTABLE", "n": 0})
    assert fb["status"] == "NOT_COMPUTABLE"
    assert fb["advised_map"] is None


def test_hyperstition_feedback_from_settled_pairs() -> None:
    # Over-confident hyperstition-like forecasts vs low outcomes → negative shift
    pairs = []
    for i, (p, o) in enumerate([(0.7, 0.0), (0.7, 0.0), (0.7, 1.0)]):
        fc = {
            "forecast_id": f"hs-{i}",
            "receipt_ref": {"integrity": "x"},
            "signal_key": "hyperstition.stage",
            "probability": p,
            "target_event": "t",
            "target_schema": "hyperstition.loop_confirmed",
            "created_at": "2026-08-05T00:00:00+00:00",
            "mapping_version": "v1",
        }
        st = settle(
            fc,
            outcome_value=o,
            settlement_decision="TRUE" if o == 1 else "FALSE",
            authority_ref="pytest",
            settle_token="pytest",
        )
        pairs.append((fc, st))
    series = score_series(pairs)
    fb = hyperstition_feedback_from_series(series)
    assert fb["status"] == "ADVISORY"
    assert fb["advised_map"] is not None
    assert fb["apply"] == "future_forecasts_only"
    # mean f=0.7, mean o≈0.33 → negative shift → advised < base for EMERGENT
    assert fb["advised_map"]["EMERGENT"] < HYPERSTITION_STAGE_PROB["EMERGENT"]
    assert fb["advised_map"]["ACTUALIZING"] < HYPERSTITION_STAGE_PROB["ACTUALIZING"]


def test_extract_forecasts_with_stage_map_override() -> None:
    result = detect_memetic_patterns("sharp steam revenge", ingest_source="mock")
    base = extract_forecasts(result)
    override = {"EMERGENT": 0.2, "ACTUALIZING": 0.55}
    adj = extract_forecasts(result, hyperstition_stage_map=override)
    base_h = next(f for f in base if f["signal_key"] == "hyperstition.stage")
    adj_h = next(f for f in adj if f["signal_key"] == "hyperstition.stage")
    assert adj_h["probability"] != base_h["probability"] or adj_h["context"].get("map_override")
    assert adj_h["context"].get("map_override") is True


def test_map_hyperstition_with_override() -> None:
    hyper = {"loop_stage": "ACTUALIZING", "mechanism": "x"}
    mapped = map_hyperstition_with_override(hyper, stage_map={"ACTUALIZING": 0.5, "EMERGENT": 0.2})
    assert mapped is not None
    assert mapped[0] == 0.5
