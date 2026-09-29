"""SELECT-007 acceptance. No training and no ledger writes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.experiment_lifecycle import preregister  # noqa: E402
from hyperlexical.select_007 import (  # noqa: E402
    EXPERIMENT_ID,
    evaluate_acceptance,
    preregistration,
    preregistration_hash,
)


def _metrics(**overrides: float) -> dict[str, float]:
    base = {
        "classification_accuracy": 0.2,
        "classify_macro_f1_nonnone": 0.2,
        "observed_label_accuracy": 0.2,
        "predicted_none_rate": 0.5,
        "unbind_clean_exact": 0.0,
    }
    base.update(overrides)
    return base


def test_preregistration_freezes_sampling_and_refuses_promotion():
    definition = preregistration()
    record = preregister(EXPERIMENT_ID, definition)
    assert record["state"] == "PREREGISTERED"
    sampling = definition["evaluation_design"]["sampling"]
    assert sampling["candidate_inferred_none_per_epoch"] == 219
    assert sampling["control_inferred_none_per_epoch"] == 1935
    assert sampling["seed_policy_defines_epoch_sampling"] is False
    assert definition["control_schedule"] == definition["candidate_schedule"]
    assert definition["promotion_policy"]["pass_promotes_best"] is False
    assert definition["promotion_policy"]["promotion_eligible"] is False
    assert len(preregistration_hash(definition)) == 64


def test_primary_gate_is_strict_and_none_rate_is_required():
    control = _metrics()
    candidate = _metrics(
        classification_accuracy=0.25,
        classify_macro_f1_nonnone=0.21,
        observed_label_accuracy=0.25,
        predicted_none_rate=0.4,
    )
    result = evaluate_acceptance(control, candidate)
    assert result["outcome"] == "PASS"
    assert result["gates"]["classify_macro_f1_nonnone"] == "PASS"
    assert result["gates"]["predicted_none_rate"] == "PASS"


def test_equal_macro_f1_fails_without_compensation():
    control = _metrics()
    candidate = _metrics(predicted_none_rate=0.1)
    result = evaluate_acceptance(control, candidate)
    assert result["outcome"] == "FAIL"
    assert result["gates"]["classify_macro_f1_nonnone"] == "FAIL"
    assert result["gates"]["predicted_none_rate"] == "PASS"


def test_missing_metric_is_fail():
    control = _metrics()
    candidate = _metrics()
    del candidate["unbind_clean_exact"]
    result = evaluate_acceptance(control, candidate)
    assert result["outcome"] == "FAIL"
    assert result["reason"] == "missing metric"
    assert "unbind_clean_exact" in result["missing"]


def test_higher_none_rate_fails_even_when_f1_improves():
    control = _metrics()
    candidate = _metrics(classify_macro_f1_nonnone=0.9, predicted_none_rate=0.8)
    result = evaluate_acceptance(control, candidate)
    assert result["outcome"] == "FAIL"
    assert result["gates"]["predicted_none_rate"] == "FAIL"
    assert result["gates"]["classify_macro_f1_nonnone"] == "PASS"
