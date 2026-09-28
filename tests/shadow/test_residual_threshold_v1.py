"""Threshold preregistration. Synthetic rows only. No development scores."""

import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.residual_threshold_v1 import (
    MIN_CALIBRATION_HIGH,
    MIN_CALIBRATION_SECONDARY,
    MIN_MEASUREMENT_HIGH,
    MIN_MEASUREMENT_PREDICTED_YES,
    MIN_PREDICTED_YES,
    OUTPUT_LABELS,
    PRECISION_FLOOR,
    WILSON_LOWER_FLOOR,
    documents,
    measurement_acceptance,
    precision_gates,
    select_threshold,
    semantic_output,
    wilson_interval,
)
from hyperlexical.selection_surface import Z95, wilson_interval as selection_wilson

MODULE = ROOT / "scripts" / "shadow" / "hyperlexical" / "residual_threshold_v1.py"
FREEZE = ROOT / "scripts" / "shadow" / "hyperlexical" / "residual_threshold_v1_freeze.py"


def _row(score, bucket, pos="noun", tier3=False, status="SCORED", **extra):
    row = {
        "glossbert_confidence": extra.pop("glossbert_confidence", "0.100000"),
        "operator_bucket": bucket,
        "pos": pos,
        "residual_score": f"{Decimal(score):.10f}",
        "score_status": status,
        "uses_tier3": tier3,
    }
    row.update(extra)
    return row


def _separated(high="0.90", secondary="0.20", high_n=12, secondary_n=8, reject="0.01"):
    rows = [_row(high, "HIGH", pos="noun") for _ in range(high_n)]
    rows.extend(_row(secondary, "SECONDARY", pos="noun") for _ in range(secondary_n))
    rows.append(_row(reject, "REJECT", pos="noun"))
    return rows


def test_wilson_matches_the_existing_selection_surface_interval():
    assert Decimal(str(Z95)) == Decimal("1.959963984540054")
    for successes, trials in ((1, 1), (3, 3), (8, 8), (8, 10), (12, 15)):
        got = wilson_interval(successes, trials)
        raw = selection_wilson(successes, trials)
        assert got is not None and raw is not None
        assert got[0] == Decimal(raw[0]).quantize(Decimal("0.000001"))
        assert got[1] == Decimal(raw[1]).quantize(Decimal("0.000001"))
    assert wilson_interval(1, 0) is None


def test_one_correct_prediction_does_not_pass_precision():
    assert precision_gates(1, 1, minimum_yes=MIN_PREDICTED_YES, precision_floor=PRECISION_FLOOR, wilson_floor=WILSON_LOWER_FLOOR) is False
    assert precision_gates(3, 3, minimum_yes=MIN_PREDICTED_YES, precision_floor=PRECISION_FLOOR, wilson_floor=WILSON_LOWER_FLOOR) is False
    assert precision_gates(8, 10, minimum_yes=MIN_PREDICTED_YES, precision_floor=PRECISION_FLOOR, wilson_floor=WILSON_LOWER_FLOOR) is False


def test_contracts_freeze_null_threshold_and_yes_unknown_only():
    docs = documents({"development_evidence_sha256": "0" * 64})
    assert set(docs) == {
        "RESIDUAL_THRESHOLD_V1_ACCEPTANCE.json",
        "RESIDUAL_THRESHOLD_V1_ARTIFACT_SCHEMA.json",
        "RESIDUAL_THRESHOLD_V1_CALIBRATION_CONTRACT.json",
        "RESIDUAL_THRESHOLD_V1_MEASUREMENT_CONTRACT.json",
        "RESIDUAL_THRESHOLD_V1_PREREGISTRATION.json",
        "RESIDUAL_THRESHOLD_V1_SELECTION_PROCEDURE.json",
        "RESIDUAL_THRESHOLD_V1_SURFACE_ISOLATION_POLICY.json",
    }
    for name, document in docs.items():
        assert document["threshold_value"] is None
        assert document["threshold_frozen"] is False
        assert document["calibration_surface_drawn"] is False
        assert document["measurement_surface_drawn"] is False
        assert document["development_rows_reusable_for_threshold_selection"] is False
        assert document["selected_source"] == "none"
        assert document["select_005_authorized"] is False
        assert document["runtime_integration"] is False
        assert document["admitted"] == document["settled"] == document["gold"] == 0
        assert document["json_schema_exists"] is False
        assert document["output_labels"] == ["YES", "UNKNOWN"]
        assert document["no_output"] == "NO"
        encoded = json.dumps(document)
        assert "semantic_noncompositional = NO" not in encoded
        assert name
    schema = docs["RESIDUAL_THRESHOLD_V1_ARTIFACT_SCHEMA.json"]
    assert schema["document_kind"] == "artifact_contract"
    assert "threshold_value" in schema["future_threshold_artifact_required_fields"]
    assert MIN_CALIBRATION_HIGH == 12
    assert MIN_CALIBRATION_SECONDARY == 8
    assert MIN_PREDICTED_YES == 8
    assert MIN_MEASUREMENT_HIGH == 12
    assert MIN_MEASUREMENT_PREDICTED_YES == 8
    assert PRECISION_FLOOR == Decimal("0.80")
    assert WILSON_LOWER_FLOOR == Decimal("0.50")


def test_highest_recall_wins_and_a_larger_threshold_breaks_ties():
    rows = [_row("0.90", "HIGH") for _ in range(9)]
    rows.extend(_row("0.50", "HIGH") for _ in range(3))
    rows.extend(_row("0.10", "SECONDARY") for _ in range(8))
    rows.append(_row("0.01", "REJECT"))
    chosen = select_threshold(rows)
    assert chosen["calibration_state"] == "THRESHOLD_FROZEN"
    assert chosen["threshold_value"] == "0.5000000000"
    tied = [_row("0.90", "HIGH") for _ in range(12)]
    tied.extend(_row("0.10", "SECONDARY") for _ in range(7))
    tied.append(_row("0.40", "SECONDARY"))
    tied.append(_row("0.01", "REJECT"))
    tie = select_threshold(tied)
    assert tie["calibration_state"] == "THRESHOLD_FROZEN"
    assert tie["threshold_value"] == "0.9000000000"
    assert select_threshold(rows) == chosen


def test_failure_states_leave_the_threshold_null():
    short = _separated(high_n=11)
    assert select_threshold(short)["calibration_state"] == "CALIBRATION_INSUFFICIENT_SUPPORT"
    assert select_threshold(short)["threshold_value"] is None
    inverted = _separated(high="0.10", secondary="0.90")
    assert select_threshold(inverted)["calibration_state"] == "NO_DIRECTIONAL_SIGNAL"
    blocked = _separated(reject="0.99")
    assert select_threshold(blocked)["calibration_state"] == "NO_THRESHOLD_PASSES_PRECISION_GATE"
    overlap = [_row("0.90", "HIGH") for _ in range(12)]
    overlap.extend(_row("0.10", "SECONDARY") for _ in range(5))
    overlap.extend(_row("0.95", "SECONDARY") for _ in range(3))
    overlap.append(_row("0.01", "REJECT"))
    missed = select_threshold(overlap)
    assert missed["calibration_state"] == "NO_THRESHOLD_PASSES_PRECISION_GATE"
    assert missed["threshold_value"] is None


def test_confound_review_and_ignored_provenance_do_not_fit_a_subgroup_threshold():
    split = [_row("0.90", "HIGH", pos="noun") for _ in range(12)]
    split.extend(_row("0.20", "SECONDARY", pos="verb") for _ in range(8))
    split.append(_row("0.01", "REJECT", pos="noun"))
    assert select_threshold(split)["calibration_state"] == "CALIBRATION_CONFOUND_REVIEW"
    left = _separated()
    right = _separated()
    for row in right:
        row["glossbert_confidence"] = "0.990000"
        row["glossbert_margin"] = "0.800000"
        row["candidate_sense_count"] = 9
    assert select_threshold(left)["threshold_value"] == select_threshold(right)["threshold_value"]
    unknown = _separated(high_n=11)
    unknown.append(_row("0.99", "HIGH", status="UNKNOWN"))
    assert select_threshold(unknown)["calibration_state"] == "CALIBRATION_INSUFFICIENT_SUPPORT"


def test_development_rows_are_refused_and_measurement_does_not_refit():
    rows = _separated()
    rows[0]["development_row"] = True
    try:
        select_threshold(rows)
    except RuntimeError as exc:
        assert "development" in str(exc)
    else:
        raise AssertionError("development row was accepted")
    clean = _separated()
    measured = measurement_acceptance(clean, "0.9000000000")
    assert measured["measurement_state"] == "MEASUREMENT_ACCEPTED"
    assert measured["applied_threshold"] == "0.9000000000"
    assert measured["threshold_adjusted"] is False
    weak = measurement_acceptance(clean, "0.0100000000")
    assert weak["measurement_state"] == "MEASUREMENT_NOT_ACCEPTED"
    assert weak["applied_threshold"] == "0.0100000000"
    assert semantic_output("SCORED", "0.9000000000", "0.5000000000") == "YES"
    assert semantic_output("SCORED", "0.4000000000", "0.5000000000") == "UNKNOWN"
    assert semantic_output("UNKNOWN", "0.9000000000", "0.5000000000") == "UNKNOWN"
    assert set(OUTPUT_LABELS) == {"YES", "UNKNOWN"}


def test_module_does_not_fit_the_development_distribution():
    source = MODULE.read_text(encoding="utf-8")
    assert "RESIDUAL_V1_MODEL_RESOLVED_REPLAY_SCORES" not in source
    assert "0.672078" not in source
    assert "0.4040327275" not in source
    assert "semantic_noncompositional = NO" not in source
    assert "torch" not in source
    freeze = FREEZE.read_text(encoding="utf-8")
    assert "select_threshold(" not in freeze
    assert "measurement_acceptance(" not in freeze
