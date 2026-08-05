"""Virality prediction + community drivers + richer neologisms."""

from __future__ import annotations

from hyperlex.analysis import (
    compute_virality_score,
    predict_virality,
    trace_semantic_variation,
    detect_neologisms,
)
from hyperlex import detect_memetic_patterns


def test_predict_virality_pure_bounds() -> None:
    p = predict_virality(
        hybrid_score=0.5,
        velocity=0.4,
        acceleration=0.5,
        lineage_confidence=0.6,
        hyperstition_stage="ACTUALIZING",
        memetic_score=0.7,
        n_neologisms=2,
    )
    assert 0.0 <= p["predicted_hybrid"] <= 0.98
    assert p["provenance"] == "SPECULATIVE"
    assert p["method"] == "feature_blend_v0"
    assert "brier" not in p
    assert p["horizon"] == "short"


def test_predict_raises_with_actualizing() -> None:
    base = predict_virality(
        hybrid_score=0.5, velocity=0.4, acceleration=0.4, hyperstition_stage="EMERGENT"
    )
    hot = predict_virality(
        hybrid_score=0.5, velocity=0.4, acceleration=0.4, hyperstition_stage="ACTUALIZING"
    )
    assert hot["predicted_hybrid"] >= base["predicted_hybrid"]


def test_analysis_attaches_prediction_not_brier() -> None:
    r = detect_memetic_patterns("sharp steam revenge", ingest_source="mock")
    assert r["provenance"]["brier"] is None
    pred = r["analysis"]["virality"]["prediction"]
    assert pred["provenance"] == "SPECULATIVE"
    assert "predicted_hybrid" in pred
    # still not a calibration forecast signal_key by default
    from hyperlex import extract_forecasts

    keys = {f["signal_key"] for f in extract_forecasts(r)}
    assert "virality.predicted" not in keys


def test_community_drivers_multi_label() -> None:
    v = trace_semantic_variation("sharp", "sharp steam betting line", lineage_family="betting-sharp")
    assert "drivers" in v
    assert "communicative_need" in v["drivers"] or "semantic_distinction" in v["drivers"]
    assert v["provenance"] == "INFERRED"


def test_neologism_compound_phrases() -> None:
    terms = detect_neologisms("sharp money and diamond hands hit the line")
    phrases = {t["term"] for t in terms}
    assert "sharp money" in phrases or "diamond hands" in phrases
    assert all(t.get("provenance") == "INFERRED" for t in terms)


def test_compute_virality_descriptive() -> None:
    v = compute_virality_score("organic velocity narrative steam coordinated spread")
    assert "hybrid_score" in v
    assert v["spread_cues"] >= 1
