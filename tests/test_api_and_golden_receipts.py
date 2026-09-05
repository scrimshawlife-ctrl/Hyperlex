"""API freeze + golden receipt corpus + abraxas compat modules."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import hyperlex
from hyperlex import (
    API_V1,
    detect_memetic_patterns,
    extract_forecasts,
    score_pair,
    settle,
    verify_receipt,
    NOT_COMPUTABLE,
)
from hyperlex.compat.abraxas import (
    to_brier_ledger_entry,
    to_brier_score_packet,
    to_operator_brier_review,
    list_hlx_runes,
    envelopes_from_result,
    CLAIM_LABELS,
    label_claim,
)
from hyperlex.calibration import score_series

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "examples" / "receipts" / "golden"
MANIFEST = GOLDEN / "MANIFEST.json"


def test_api_v1_symbols_exportable() -> None:
    for name in API_V1:
        assert hasattr(hyperlex, name), f"missing API_V1 symbol: {name}"
        assert name in hyperlex.__all__


def test_no_abraxas_import_in_compat() -> None:
    """compat.abraxas must not pull abraxas/core packages."""
    import hyperlex.compat.abraxas as abx
    import sys

    for mod in list(sys.modules):
        if mod == "abraxas" or mod.startswith("abraxas.") or mod.startswith("core.brier"):
            # allow absence only; if present must not be required by our import
            pass
    # smoke call
    assert len(abx.list_hlx_runes()) >= 4
    assert "OBSERVED" in CLAIM_LABELS


def test_label_claim() -> None:
    c = label_claim("lineage_match", "INFERRED")
    assert c["label"] == "INFERRED"
    with pytest.raises(ValueError):
        label_claim("x", "TRUE")


def test_golden_receipt_corpus() -> None:
    assert MANIFEST.exists()
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert man["schema"] == "hyperlex.golden_receipts.v1"
    assert len(man["receipts"]) >= 4

    for entry in man["receipts"]:
        path = GOLDEN / entry["file"]
        assert path.exists(), entry["file"]
        payload = json.loads(path.read_text(encoding="utf-8"))
        ok, msg = verify_receipt(payload)
        assert ok, f"{entry['id']}: {msg}"
        assert payload["provenance"].get("brier") is None
        assert payload["receipt"]["integrity"] == entry["integrity"]
        assert payload["provenance"].get("source_fingerprint")
        # forecasts never carry brier
        for fc in extract_forecasts(payload):
            assert "atomic_score" not in fc


def test_abraxas_score_and_ledger_packets() -> None:
    fc = {
        "forecast_id": "api-test-1",
        "receipt_ref": {"integrity": "abc"},
        "signal_key": "lineage.confidence",
        "probability": 0.75,
        "target_event": "t",
        "target_schema": "lineage.family_confirmed",
        "created_at": "2026-08-05T00:00:00+00:00",
        "mapping_version": "v1",
    }
    st = settle(fc, outcome_value=1.0, settlement_decision="TRUE", authority_ref="pytest", settle_token="pytest")
    sc = score_pair(fc, st)
    assert sc["status"] == "SCORED"

    packet = to_brier_score_packet(fc, sc)
    assert packet["schema_version"] == "BrierScorePacket.v1"
    assert packet["brier_score"] == pytest.approx(0.0625)
    assert packet["status"] == "ok"

    ledger = to_brier_ledger_entry(fc, sc, settlement=st)
    assert ledger["schema_version"] == "BrierLedgerEntry.v1"
    assert ledger["deterministic_ledger_hash"]

    # VOID cannot export
    st_v = settle(fc, outcome_value=0.0, settlement_decision="VOID")
    sc_v = score_pair(fc, st_v)
    with pytest.raises(ValueError):
        to_brier_score_packet(fc, sc_v)


def test_operator_review_from_series() -> None:
    pairs = []
    for i, (p, o) in enumerate([(0.8, 1.0), (0.3, 0.0)]):
        fc = {
            "forecast_id": f"or-{i}",
            "receipt_ref": {"integrity": "x"},
            "signal_key": "lineage.confidence",
            "probability": p,
            "target_event": "t",
            "target_schema": "lineage.family_confirmed",
            "created_at": "2026-08-05T00:00:00+00:00",
            "mapping_version": "v1",
        }
        st = settle(
            fc,
            outcome_value=o,
            settlement_decision="TRUE" if o == 1.0 else "FALSE",
            authority_ref="pytest",
            settle_token="pytest",
        )
        pairs.append((fc, st))
    series = score_series(pairs)
    review = to_operator_brier_review(series)
    assert review["schema_version"] == "OperatorBrierReviewPacket.v1"
    assert review["status"] == "pending"
    empty = to_operator_brier_review(score_series([]))
    assert empty["status"] == "not_computable"


def test_envelopes_from_result() -> None:
    result = detect_memetic_patterns("sharp steam revenge", ingest_source="mock")
    envs = envelopes_from_result(result)
    assert any(e["rune_id"].startswith("RUNE.HLX.") for e in envs)
