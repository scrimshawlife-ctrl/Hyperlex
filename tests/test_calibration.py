"""Golden fixtures for lineage confidence, Brier scoring, and score log."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from hyperlex.analysis import compute_lineage_confidence, match_lineage
from hyperlex.calibration import (
    NOT_COMPUTABLE,
    extract_forecasts,
    score_pair,
    score_series,
    settle,
    settle_and_log,
    recompute_series,
    append_forecast,
    to_brier_ledger_entry,
    mean_shift_from_series,
    apply_mean_shift,
    verify_chain,
    brier_atomic,
)
from hyperlex.calibration.scoring import (
    murphy_decomposition_ferro,
    yates_vieira,
    discrimination_slope,
)
from hyperlex import detect_memetic_patterns


# ---------------------------------------------------------------------------
# Lineage confidence golden fixtures
# ---------------------------------------------------------------------------

def test_lineage_confidence_empty_hits() -> None:
    score, breakdown = compute_lineage_confidence([], ["sharp money", "steam"], "noop")
    assert score == 0.0
    assert breakdown["n_hits"] == 0


def test_lineage_confidence_known_formula() -> None:
    """Hand-checked formula for a single multi-word hit."""
    hits = ["sharp money"]
    family = ["sharp money", "steam", "juice", "closing line value", "clv"]
    corpus = "sharp money hit the market"
    score, breakdown = compute_lineage_confidence(hits, family, corpus)

    # weight = min(0.75, 0.22 + 0.14*2 + 0.025*min(11,24)) = min(0.75, 0.22+0.28+0.275) = 0.75
    expected_specificity = 0.75
    expected_coverage = 1 / 5
    expected_hit_bonus = 0.12  # first hit: max(0.04, 0.12)
    expected_density = 0.0
    expected_raw = 0.18 + expected_specificity * 0.38 + expected_coverage * 0.22 + expected_hit_bonus + expected_density

    assert breakdown["n_hits"] == 1
    assert breakdown["specificity"] == pytest.approx(expected_specificity, abs=0.001)
    assert breakdown["coverage"] == pytest.approx(expected_coverage, abs=0.001)
    assert breakdown["hit_bonus"] == pytest.approx(expected_hit_bonus, abs=0.001)
    assert score == pytest.approx(min(0.98, max(0.0, expected_raw)), abs=0.001)
    assert "term_weights" in breakdown


def test_match_lineage_sharp_family() -> None:
    text = "sharp steam square wiseguy hammer revenge low block"
    lineage = match_lineage(text, min_confidence=0.42)
    assert lineage is not None
    assert lineage["family_id"] == "betting-sharp"
    assert lineage["confidence"] >= 0.42
    assert lineage["provenance"] == "INFERRED"
    assert "score_breakdown" in lineage


def test_match_lineage_below_threshold_returns_none() -> None:
    # Unrelated text should not match any family at default threshold
    lineage = match_lineage("the weather is cloudy today with light rain", min_confidence=0.42)
    assert lineage is None


# ---------------------------------------------------------------------------
# score_pair / score_series golden
# ---------------------------------------------------------------------------

def _fc(fid: str, p: float, signal: str = "lineage.confidence") -> dict:
    return {
        "forecast_id": fid,
        "receipt_ref": {"integrity": "abc123"},
        "signal_key": signal,
        "probability": p,
        "target_event": "test",
        "target_schema": "lineage.family_confirmed",
        "created_at": "2026-08-05T00:00:00+00:00",
        "mapping_version": "v1",
        "provenance": "INFERRED",
    }


def _st(fid: str, o: float, decision: str = "TRUE") -> dict:
    kwargs = {}
    if str(decision).upper() in ("TRUE", "FALSE"):
        kwargs = {"authority_ref": "pytest", "settle_token": "pytest"}
    return settle(_fc(fid, 0.5), outcome_value=o, settlement_decision=decision, **kwargs)


def test_brier_atomic_known() -> None:
    assert brier_atomic(0.7, 1.0) == pytest.approx(0.09)
    assert brier_atomic(0.7, 0.0) == pytest.approx(0.49)
    assert brier_atomic(0.0, 0.0) == 0.0
    assert brier_atomic(1.0, 1.0) == 0.0


def test_score_pair_scored() -> None:
    fc = _fc("f1", 0.8)
    st = settle(fc, outcome_value=1.0, settlement_decision="TRUE", authority_ref="pytest", settle_token="pytest")
    rec = score_pair(fc, st)
    assert rec["status"] == "SCORED"
    assert rec["atomic_score"] == pytest.approx(0.04)
    assert rec["forecast_id"] == "f1"


def test_score_pair_void_not_computable() -> None:
    fc = _fc("f2", 0.6)
    st = settle(fc, outcome_value=0.0, settlement_decision="VOID")
    rec = score_pair(fc, st)
    assert rec["status"] == NOT_COMPUTABLE
    assert "atomic_score" not in rec


def test_score_pair_id_mismatch() -> None:
    fc = _fc("f3", 0.5)
    st = settle(_fc("other", 0.5), outcome_value=1.0, settlement_decision="TRUE", authority_ref="pytest", settle_token="pytest")
    rec = score_pair(fc, st)
    assert rec["status"] == NOT_COMPUTABLE
    assert "mismatch" in rec["reason"]


def test_score_series_empty_not_computable() -> None:
    series = score_series([])
    assert series["status"] == NOT_COMPUTABLE
    assert series["n"] == 0
    assert series["series_brier"] == NOT_COMPUTABLE
    assert series["murphy"]["reliability"] == NOT_COMPUTABLE
    assert series["murphy_ferro"]["reliability"] == NOT_COMPUTABLE
    assert series["yates"]["bias_squared"] == NOT_COMPUTABLE
    assert series["yates_vieira"]["variance_mismatch"] == NOT_COMPUTABLE
    assert series["discrimination"]["delta_f"] == NOT_COMPUTABLE


def test_score_series_two_pairs_known_bs() -> None:
    # f=0.8 o=1 → 0.04; f=0.3 o=0 → 0.09; mean BS = 0.065
    pairs = []
    for fid, p, o, dec in [("a", 0.8, 1.0, "TRUE"), ("b", 0.3, 0.0, "FALSE")]:
        fc = _fc(fid, p)
        st = settle(fc, outcome_value=o, settlement_decision=dec, authority_ref="pytest", settle_token="pytest")
        pairs.append((fc, st))

    series = score_series(pairs)
    assert series["status"] == "SCORED"
    assert series["n"] == 2
    assert series["series_brier"] == pytest.approx(0.065)
    assert isinstance(series["murphy_ferro"]["reliability"], float)
    assert isinstance(series["yates_vieira"]["bias_squared"], float)
    assert series["discrimination"]["delta_f"] == pytest.approx(0.8 - 0.3)
    # BSS vs climatology: mean o = 0.5, ref BS = 0.25
    assert series["brier_skill_score"] == pytest.approx(1.0 - (0.065 / 0.25))


def test_score_series_skips_void() -> None:
    fc1 = _fc("v1", 0.9)
    st1 = settle(fc1, outcome_value=1.0, settlement_decision="TRUE", authority_ref="pytest", settle_token="pytest")
    fc2 = _fc("v2", 0.1)
    st2 = settle(fc2, outcome_value=0.0, settlement_decision="VOID")
    series = score_series([(fc1, st1), (fc2, st2)])
    assert series["n"] == 1
    assert series["series_brier"] == pytest.approx(0.01)


def test_yates_vieira_non_negative() -> None:
    preds = [0.2, 0.4, 0.7, 0.9]
    targs = [0.0, 0.0, 1.0, 1.0]
    yv = yates_vieira(preds, targs)
    assert yv["variance_mismatch"] >= 0
    assert yv["correlation_deficit"] >= 0
    assert yv["bias_squared"] >= 0
    assert yv["brier_score"] == pytest.approx(
        yv["variance_mismatch"] + yv["correlation_deficit"] + yv["bias_squared"],
        abs=1e-9,
    )


def test_discrimination_needs_both_classes() -> None:
    d = discrimination_slope([0.8, 0.9], [1.0, 1.0])
    assert d["delta_f"] == NOT_COMPUTABLE
    assert d["n_pos"] == 2
    assert d["n_neg"] == 0


def test_murphy_ferro_small_n() -> None:
    preds = [0.1, 0.9]
    targs = [0.0, 1.0]
    m = murphy_decomposition_ferro(preds, targs)
    assert m["correction"] == "ferro_fricker"
    assert isinstance(m["reliability"], float)
    assert m["reliability"] >= 0


# ---------------------------------------------------------------------------
# extract_forecasts + score log operator path
# ---------------------------------------------------------------------------

def test_extract_forecasts_from_analysis() -> None:
    result = detect_memetic_patterns(
        query="sharp money steam closing line value revenge",
        ingest_source="mock",
        validate=False,
    )
    # brier must stay null on open analysis
    assert result["provenance"].get("brier") is None

    forecasts = extract_forecasts(result, receipt_ref={"integrity": "testint"})
    assert isinstance(forecasts, list)
    # lineage and/or virality/hyperstition may emit
    for fc in forecasts:
        assert "forecast_id" in fc
        assert 0.0 <= fc["probability"] <= 1.0
        assert fc["mapping_version"] == "v1"
        assert "atomic_score" not in fc  # never attach Brier to forecast


def test_settle_and_log_roundtrip(tmp_path: Path) -> None:
    log = tmp_path / "score_log.jsonl"
    fc = _fc("logtest1", 0.75)
    append_forecast(fc, path=log)

    out = settle_and_log(
        fc,
        outcome_value=1.0,
        settlement_decision="TRUE",
        authority_ref="pytest",
        authority_note="operator confirmed family",
        settle_token="pytest",
        path=log,
    )
    assert out["scorable"] is True
    assert out["score"]["status"] == "SCORED"
    assert out["score"]["atomic_score"] == pytest.approx((0.75 - 1.0) ** 2)

    chain = verify_chain(log)
    assert chain["ok"] is True
    assert chain["n"] >= 2  # forecast + settlement + score (or settlement+score if forecast already)

    series = recompute_series(path=log)
    assert series["status"] == "SCORED"
    assert series["n"] == 1
    assert series["series_brier"] == pytest.approx(0.0625)


def test_recompute_series_empty_log(tmp_path: Path) -> None:
    log = tmp_path / "empty.jsonl"
    series = recompute_series(path=log)
    assert series["status"] == NOT_COMPUTABLE
    assert series["n"] == 0


def test_to_brier_ledger_entry_compatible() -> None:
    fc = _fc("led1", 0.6)
    st = settle(fc, outcome_value=0.0, settlement_decision="FALSE", authority_ref="pytest", settle_token="pytest")
    sc = score_pair(fc, st)
    entry = to_brier_ledger_entry(fc, sc, settlement=st)
    assert entry["schema_version"] == "BrierLedgerEntry.v1"
    assert entry["status"] == "recorded"
    assert len(entry["deterministic_ledger_hash"]) == 64
    # hash formula must match Abraxas
    from hyperlex.calibration.export import compute_ledger_hash

    assert entry["deterministic_ledger_hash"] == compute_ledger_hash(
        entry["forecast_hash"],
        entry["score_hash"],
        entry["calibration_hash"],
        entry["ledger_generation"],
    )


def test_to_brier_ledger_entry_fail_closed() -> None:
    fc = _fc("led2", 0.5)
    st = settle(fc, outcome_value=0.0, settlement_decision="VOID")
    sc = score_pair(fc, st)
    with pytest.raises(ValueError, match="settlement required"):
        to_brier_ledger_entry(fc, sc, settlement=st)


def test_mean_shift_advisory() -> None:
    pairs = []
    for i, (p, o) in enumerate([(0.9, 0.0), (0.8, 0.0), (0.85, 1.0)]):
        fc = _fc(f"ms{i}", p)
        st = settle(
            fc,
            outcome_value=o,
            settlement_decision="TRUE" if o == 1.0 else "FALSE",
            authority_ref="pytest",
            settle_token="pytest",
        )
        pairs.append((fc, st))
    series = score_series(pairs)
    advisory = mean_shift_from_series(series)
    assert advisory["status"] == "ADVISORY"
    assert isinstance(advisory["shift"], float)
    # mean f high, mean o ~0.33 → negative shift
    assert advisory["shift"] < 0
    assert apply_mean_shift(0.9, advisory["shift"]) <= 0.9


def test_mean_shift_empty_not_computable() -> None:
    advisory = mean_shift_from_series(score_series([]))
    assert advisory["status"] == "NOT_COMPUTABLE"


# ---------------------------------------------------------------------------
# CLI operator settlement path
# ---------------------------------------------------------------------------

import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "hyperlex.py"


def _cli(*args: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = __import__("os").environ.copy()
    env["HYPERLEX_OFFLINE"] = "1"
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=ROOT,
    )


def test_cli_forecasts_settle_score_series(tmp_path: Path) -> None:
    log = tmp_path / "op_score_log.jsonl"
    result_path = tmp_path / "analysis.json"

    analyze = _cli(
        "analyze",
        "--query", "sharp steam square wiseguy revenge hammer",
        "--source", "mock",
        "--forecasts",
        "--append-log",
        "--log", str(log),
        "--out", str(result_path),
    )
    assert analyze.returncode == 0, analyze.stderr
    body = json.loads(analyze.stdout)
    assert body["ok"] is True
    forecasts = body.get("forecasts") or []
    assert isinstance(forecasts, list)
    # may be empty if no mappable signals; force a settle path with extract if needed
    if not forecasts:
        # still exercise empty score-series fail-closed
        ss = _cli("score-series", "--log", str(log))
        assert ss.returncode == 0
        ss_body = json.loads(ss.stdout)
        assert ss_body["series"]["status"] == NOT_COMPUTABLE
        return

    fc = forecasts[0]
    fid = fc["forecast_id"]
    settle_cmd = _cli(
        "settle",
        "--forecast-id", fid,
        "--decision", "TRUE",
        "--authority-ref", "pytest",
        "--authority-note", "fixture confirm",
        "--settle-token", "pytest",
        "--export-ledger",
        "--log", str(log),
    )
    assert settle_cmd.returncode == 0, settle_cmd.stderr
    settle_body = json.loads(settle_cmd.stdout)
    assert settle_body["score"]["status"] == "SCORED"
    assert settle_body["ledger_entry"]["schema_version"] == "BrierLedgerEntry.v1"

    ss = _cli("score-series", "--log", str(log), "--mean-shift", "--verify-chain")
    assert ss.returncode == 0, ss.stderr
    ss_body = json.loads(ss.stdout)
    assert ss_body["series"]["status"] == "SCORED"
    assert ss_body["series"]["n"] >= 1
    assert ss_body["chain"]["ok"] is True
